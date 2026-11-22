import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parent
DATA = BASE / "data"
SOURCES_FILE = DATA / "sources.json"
REPORT_FILE = DATA / "collection_report.json"


def load_sources():
    with SOURCES_FILE.open(encoding="utf-8") as handle:
        return json.load(handle)


def verify_live(source, timeout):
    try:
        import requests
    except ImportError:
        return {"status": "skipped", "detail": "requests unavailable"}

    try:
        response = requests.get(
            source["url"],
            timeout=timeout,
            headers={"User-Agent": "scheme-chatbot-prototype/0.1 research"},
        )
        return {
            "status": "ok" if response.ok else "http_error",
            "http_status": response.status_code,
            "bytes": len(response.content),
            "content_sha256": hashlib.sha256(response.content).hexdigest()[:16],
        }
    except Exception as exc:
        return {"status": "network_error", "detail": type(exc).__name__}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true", help="attempt live URL verification")
    parser.add_argument("--timeout", type=int, default=8)
    args = parser.parse_args()

    bundle = load_sources()
    sources = bundle["sources"]
    report = {
        "collected_at_utc": datetime.now(timezone.utc).isoformat(),
        "method": bundle["collection_method"],
        "source_count": len(sources),
        "tier_counts": {},
        "type_counts": {},
        "live_verification": args.live,
        "verification": [],
    }

    for source in sources:
        report["tier_counts"][source["tier"]] = report["tier_counts"].get(source["tier"], 0) + 1
        report["type_counts"][source["source_type"]] = report["type_counts"].get(source["source_type"], 0) + 1
        record = {"id": source["id"], "url": source["url"], "snapshot": "search_tool_excerpt"}
        if args.live:
            record.update(verify_live(source, args.timeout))
        report["verification"].append(record)

    missing = [s["id"] for s in sources if not all(k in s for k in ("url", "title", "facts", "snippet"))]
    report["schema_validation"] = "pass" if not missing else "fail"
    report["invalid_sources"] = missing

    REPORT_FILE.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "verification"}, ensure_ascii=False, indent=2))
    print(f"report: {REPORT_FILE}")
    return 0 if report["schema_validation"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
