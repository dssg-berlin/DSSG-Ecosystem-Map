from __future__ import annotations

import hashlib
import io
import json
import re
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
USER_AGENT = "Mozilla/5.0 (compatible; LexAuditPrototype/0.1; research)"

SOURCES = {
    "GDPR": {
        "url": "https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32016R0679",
        "file": "gdpr_32016R0679.html",
        "kind": "eurlex_html",
        "instrument": "GDPR",
        "citation_prefix": "Regulation (EU) 2016/679",
        "unit": "Article",
    },
    "AI_ACT": {
        "url": "https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32024R1689",
        "file": "ai_act_32024R1689.html",
        "kind": "eurlex_html",
        "instrument": "EU AI Act",
        "citation_prefix": "Regulation (EU) 2024/1689",
        "unit": "Article",
    },
    "DPDP": {
        "url": "https://www.meity.gov.in/static/uploads/2024/02/Digital-Personal-Data-Protection-Act-2023.pdf",
        "file": "dpdp_act_2023.pdf",
        "kind": "pdf",
        "instrument": "India DPDP Act",
        "citation_prefix": "Digital Personal Data Protection Act, 2023",
        "unit": "Section",
    },
}

DPDP_TITLES = {
    1: "Short title and commencement",
    2: "Definitions",
    3: "Application of Act",
    4: "Grounds for processing personal data",
    5: "Notice",
    6: "Consent",
    7: "Certain legitimate uses",
    8: "General obligations of Data Fiduciary",
    9: "Processing of personal data of children",
    10: "Other obligations of Significant Data Fiduciary",
    11: "Right of access and information",
    12: "Right to correction, completion, updating and erasure",
    13: "Right to grievance redressal",
    14: "Right to nominate",
    15: "Duties of Data Principal",
    16: "Restrictions on transfer of personal data outside India",
    17: "Exemptions",
    18: "Establishment of Board",
    19: "Constitution of Board",
    20: "Salary, allowances and terms of service of Chairperson and Members",
    21: "Disqualification, removal and restoration",
    22: "Resignation",
    23: "Procedure",
    24: "Officers and employees of Board",
    25: "Acts and proceedings of Board",
    26: "Powers of Chairperson",
    27: "Powers and functions of Board",
    28: "Functions of Board",
    29: "Appeal to Appellate Tribunal",
    30: "Execution of orders of Appellate Tribunal",
    31: "Mediation",
    32: "Voluntary undertaking",
    33: "Penalties",
    34: "Penalty proceeds",
    35: "Protection of action taken in good faith",
    36: "Power to call for information",
    37: "Power of entry and search",
    38: "Act to be in addition to and not in derogation of other laws",
    39: "Bar on jurisdiction of civil courts",
    40: "Power to make rules",
    41: "Power to remove difficulties",
    42: "Repeal and savings",
    43: "Amendment",
}

WATERMARK_PATTERNS = [
    r"^vlk/kkj\.k",
    r"^EXTRAORDINARY",
    r"^PART II",
    r"^izkf",
    r"^PUBLISHED\s+BY\s+AUTHORITY",
    r"^No\.\s*25\]",
    r"^bl Hkkx",
    r"^CG-DL-E-",
    r"^सी\.जी\.",
    r"^THE GAZETTE OF INDIA",
    r"^Separate paging",
    r"^xxxGID",
    r"^jftLV",
    r"^\d+\s+THE GAZETTE",
]


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("\u00a0", " ").replace("\u2009", " ").replace("\n", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def clean_dpdp_text(raw: str) -> str:
    kept = []
    for line in raw.splitlines():
        stripped = line.strip()
        if any(re.match(pattern, stripped) for pattern in WATERMARK_PATTERNS):
            continue
        kept.append(stripped)
    return "\n".join(kept)


def fetch_source(meta: dict) -> dict:
    RAW.mkdir(parents=True, exist_ok=True)
    target = RAW / meta["file"]
    response = requests.get(meta["url"], headers={"User-Agent": USER_AGENT}, timeout=180)
    response.raise_for_status()
    payload = response.content
    target.write_bytes(payload)
    return {
        "url": meta["url"],
        "raw_file": str(target.relative_to(ROOT)),
        "sha256": sha256_bytes(payload),
        "bytes": len(payload),
        "content_type": response.headers.get("content-type", ""),
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
    }


def parse_eurlex(key: str, meta: dict, raw_bytes: bytes, provenance: dict) -> list[dict]:
    soup = BeautifulSoup(raw_bytes, "lxml")
    full_text = normalize(soup.get_text(" "))
    (PROCESSED / f"{key.lower()}_source_normalized.txt").write_text(
        full_text, encoding="utf-8"
    )
    provisions = []
    seen = set()
    for div in soup.select('div.eli-subdivision[id^="art_"]'):
        identifier = div.get("id", "")
        if not re.fullmatch(r"art_\d+", identifier):
            continue
        number = identifier.split("_")[1]
        if number in seen:
            continue
        seen.add(number)
        title_node = div.select_one("p.oj-sti-art") or div.select_one(".eli-title")
        title = normalize(title_node.get_text(" ")) if title_node else ""
        clone = BeautifulSoup(str(div), "lxml")
        for node in clone.select("p.oj-ti-art, p.oj-sti-art"):
            node.decompose()
        body = normalize(clone.get_text(" "))
        excerpt = body[:280]
        verified = bool(excerpt) and excerpt in full_text
        provisions.append(
            {
                "provision_id": f'{meta["instrument"]}:ART:{number}',
                "instrument": meta["instrument"],
                "unit": "Article",
                "number": number,
                "title": title,
                "citation": f'{meta["citation_prefix"]}, Article {number}',
                "text": body,
                "excerpt": excerpt,
                "citation_verified": verified,
                "source_url": meta["url"],
                "source_sha256": provenance["sha256"],
                "source_file": provenance["raw_file"],
            }
        )
    return sorted(provisions, key=lambda p: int(p["number"]))


def parse_dpdp(key: str, meta: dict, raw_bytes: bytes, provenance: dict) -> list[dict]:
    reader = PdfReader(io.BytesIO(raw_bytes))
    raw_text = "\n".join(page.extract_text() or "" for page in reader.pages)
    cleaned = clean_dpdp_text(raw_text)
    full_text = normalize(cleaned)
    (PROCESSED / f"{key.lower()}_source_normalized.txt").write_text(
        full_text, encoding="utf-8"
    )
    markers = []
    for match in re.finditer(r"(?m)^\s*(\d{1,2})\.\s+", cleaned):
        number = int(match.group(1))
        if 1 <= number <= 43:
            markers.append((number, match.start()))
    first_seen = {}
    for number, position in markers:
        first_seen.setdefault(number, position)
    ordered = sorted(first_seen.items(), key=lambda item: item[1])
    provisions = []
    for index, (number, start) in enumerate(ordered):
        end = ordered[index + 1][1] if index + 1 < len(ordered) else len(cleaned)
        body = normalize(cleaned[start:end])
        excerpt = body[:280]
        verified = bool(excerpt) and excerpt in full_text
        provisions.append(
            {
                "provision_id": f'DPDP:SEC:{number}',
                "instrument": meta["instrument"],
                "unit": "Section",
                "number": str(number),
                "title": DPDP_TITLES.get(number, f"Section {number}"),
                "citation": f'{meta["citation_prefix"]}, section {number}',
                "text": body,
                "excerpt": excerpt,
                "citation_verified": verified,
                "source_url": meta["url"],
                "source_sha256": provenance["sha256"],
                "source_file": provenance["raw_file"],
            }
        )
    return provisions


def main() -> int:
    PROCESSED.mkdir(parents=True, exist_ok=True)
    manifest = {
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "collector_version": "0.1.0",
        "sources": {},
        "counts": {},
    }
    all_provisions = []
    for key, meta in SOURCES.items():
        provenance = fetch_source(meta)
        payload = (RAW / meta["file"]).read_bytes()
        if meta["kind"] == "eurlex_html":
            provisions = parse_eurlex(key, meta, payload, provenance)
        else:
            provisions = parse_dpdp(key, meta, payload, provenance)
        out_file = PROCESSED / f"{key.lower()}_provisions.json"
        out_file.write_text(
            json.dumps(provisions, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        manifest["sources"][key] = provenance
        manifest["counts"][key] = len(provisions)
        all_provisions.extend(provisions)
        print(
            f"{key}: {len(provisions)} provisions, "
            f"{sum(p['citation_verified'] for p in provisions)} citation-verified"
        )
    (PROCESSED / "all_provisions.json").write_text(
        json.dumps(all_provisions, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (PROCESSED / "manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
