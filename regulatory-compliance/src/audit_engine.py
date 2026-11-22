from __future__ import annotations

import fnmatch
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
KG_DIR = ROOT / "data" / "knowledge_graph"
RESULTS = ROOT / "results" / "audits"

SKIP_DIRS = {
    ".git",
    "__pycache__",
    ".venv",
    "node_modules",
    ".mypy_cache",
    ".pytest_cache",
    "results",
    "data",
}
MAX_FILE_BYTES = 2_000_000
SEVERITY_ORDER = {"critical": 4, "high": 3, "medium": 2, "low": 1}


def instrument_group(instrument: str) -> str:
    if instrument == "GDPR":
        return "EU GDPR"
    if instrument == "EU AI Act":
        return "EU AI Act"
    return "India DPDP Act"


class AuditEngine:
    def __init__(self, control_index: list[dict], provisions: list[dict]) -> None:
        self.controls = control_index
        self.controls_by_id = {c["id"]: c for c in control_index}
        self.provisions = {p["provision_id"]: p for p in provisions}
        self._counter = 0
        self._seen: set[tuple[str, str, str]] = set()

    def _finding(
        self,
        control: dict,
        message: str,
        evidence: str,
        location: dict,
    ) -> dict:
        dedup_key = (control["id"], location.get("file", ""), evidence[:160])
        if dedup_key in self._seen:
            return {}
        self._seen.add(dedup_key)
        self._counter += 1
        citations = []
        for citation in control["resolved_citations"]:
            citations.append(
                {
                    "provision_id": citation["provision_id"],
                    "citation": citation["citation"],
                    "title": citation["title"],
                    "excerpt": citation["excerpt"],
                    "source_url": citation["source_url"],
                    "source_sha256": citation["source_sha256"],
                    "verified": citation["verified"],
                }
            )
        jurisdictions = sorted(
            {instrument_group(self.provisions[c["provision_id"]]["instrument"]) for c in citations}
        )
        return {
            "finding_id": f"F{self._counter:03d}",
            "control_id": control["id"],
            "control_title": control["title"],
            "severity": control["severity"],
            "theme": control["theme"],
            "jurisdictions": jurisdictions,
            "message": message,
            "evidence": evidence[:500],
            "location": location,
            "citations": citations,
            "remediation": " ".join(control["remediation"].split()),
        }

    def _files(self, root: Path, globs: Iterable[str]) -> list[Path]:
        patterns = list(globs) or ["*"]
        result = []
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            if any(part in SKIP_DIRS for part in path.parts):
                continue
            if path.stat().st_size > MAX_FILE_BYTES:
                continue
            if any(fnmatch.fnmatch(path.name, pattern) for pattern in patterns):
                result.append(path)
        return sorted(result)

    @staticmethod
    def _read(path: Path) -> str:
        try:
            return path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return ""

    def audit_codebase(self, root: Path) -> list[dict]:
        root = root.resolve()
        findings = []
        for control in self.controls:
            for detector in control.get("code_patterns", []):
                regex = re.compile(detector["regex"])
                for path in self._files(root, detector.get("globs", ["*"])):
                    text = self._read(path)
                    matches = []
                    for number, line in enumerate(text.splitlines(), start=1):
                        match = regex.search(line)
                        if match:
                            matches.append((number, line.strip()[:300]))
                            if len(matches) >= 3:
                                break
                    for number, line in matches:
                        finding = self._finding(
                            control,
                            detector["message"],
                            line,
                            {"file": str(path.relative_to(root)), "line": number},
                        )
                        if finding:
                            findings.append(finding)
            absence = control.get("absence_check")
            if absence:
                applies = [
                    re.compile(token, re.IGNORECASE)
                    for token in absence.get("applies_when_any", [])
                ]
                required = [
                    re.compile(token, re.IGNORECASE)
                    for token in absence.get("require_any", [])
                ]
                files = self._files(root, absence.get("globs", ["*"]))
                corpus = [(path, self._read(path)) for path in files]
                trigger_files = []
                for path, text in corpus:
                    if any(pattern.search(text) for pattern in applies):
                        trigger_files.append(str(path.relative_to(root)))
                satisfied = any(
                    any(pattern.search(text) for pattern in required)
                    for _path, text in corpus
                )
                if trigger_files and not satisfied:
                    finding = self._finding(
                        control,
                        absence["message"],
                        f"trigger files: {', '.join(trigger_files[:8])} "
                        f"({len(trigger_files)} total); none contained "
                        f"{', '.join(absence['require_any'][:5])}",
                        {"file": None, "line": None, "scope": "repository"},
                    )
                    if finding:
                        findings.append(finding)
        return self._sort(findings)

    def audit_trace(self, path: Path) -> list[dict]:
        events = []
        for number, line in enumerate(
            path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1
        ):
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                event = {"raw": line}
            event["_line"] = number
            events.append(event)
        findings = []

        for control in self.controls:
            for detector in control.get("trace_patterns", []):
                regex = re.compile(detector["regex"], re.IGNORECASE)
                fields = detector.get("fields", ["raw"])
                for event in events:
                    chunks = []
                    for field in fields:
                        value = event.get(field)
                        if value is None:
                            continue
                        chunks.append(
                            value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
                        )
                    payload = " | ".join(chunks)
                    match = regex.search(payload)
                    if match:
                        finding = self._finding(
                            control,
                            detector["message"],
                            payload[:300],
                            {"file": str(path), "line": event["_line"], "event": event.get("event", "unknown")},
                        )
                        if finding:
                            findings.append(finding)

        findings.extend(self._trace_semantics(events, path))
        return self._sort(findings)

    def _trace_semantics(self, events: list[dict], path: Path) -> list[dict]:
        findings = []
        pii = re.compile(
            r"\b(email|aadhaar|aadhar|pan_card|ssn|passport|phone|mobile)\b\s*[:=]\s*"
            r"\"?[A-Za-z0-9@._+-]{4,}",
            re.IGNORECASE,
        )
        declared_purposes = set()
        for event in events:
            if event.get("event") == "session_start":
                declared_purposes.update(
                    str(p).lower() for p in event.get("declared_purposes", [])
                )

        for event in events:
            event_type = str(event.get("event", "")).lower()
            line = event["_line"]
            if event_type in {"log", "tool_result", "tool_call"} and pii.search(
                json.dumps(event, ensure_ascii=False)
            ):
                control = self.controls_by_id["C01"]
                finding = self._finding(
                    control,
                    "Live trace event exposes an unmasked personal identifier.",
                    json.dumps({k: v for k, v in event.items() if k != "_line"}, ensure_ascii=False),
                    {"file": str(path), "line": line, "event": event_type},
                )
                if finding:
                    findings.append(finding)

            if event_type in {"decision", "automated_decision"}:
                adverse = bool(event.get("adverse", False))
                if not event.get("explanation") and not event.get("reason_codes"):
                    control = self.controls_by_id["C09"]
                    finding = self._finding(
                        control,
                        "Automated decision in live trace has no explanation or reason codes.",
                        json.dumps(event, ensure_ascii=False),
                        {"file": str(path), "line": line, "event": event_type},
                    )
                    if finding:
                        findings.append(finding)
                if adverse and not event.get("human_review"):
                    control = self.controls_by_id["C10"]
                    finding = self._finding(
                        control,
                        "Adverse automated decision proceeded without recorded human review.",
                        json.dumps(event, ensure_ascii=False),
                        {"file": str(path), "line": line, "event": event_type},
                    )
                    if finding:
                        findings.append(finding)

            if event_type in {"generated_content", "synthetic"}:
                disclosed = any(
                    event.get(key)
                    for key in ("ai_generated", "synthetic_content", "disclosure", "watermark")
                )
                if not disclosed:
                    control = self.controls_by_id["C11"]
                    finding = self._finding(
                        control,
                        "Generated content emitted in live trace without an AI-origin disclosure flag.",
                        json.dumps(event, ensure_ascii=False),
                        {"file": str(path), "line": line, "event": event_type},
                    )
                    if finding:
                        findings.append(finding)

            if event_type in {"tool_call", "tool_result"} and event.get("purpose"):
                purpose = str(event["purpose"]).lower()
                if declared_purposes and purpose not in declared_purposes:
                    control = self.controls_by_id["C25"]
                    finding = self._finding(
                        control,
                        f"Agent tool event uses undeclared purpose '{purpose}'.",
                        json.dumps(event, ensure_ascii=False),
                        {"file": str(path), "line": line, "event": event_type},
                    )
                    if finding:
                        findings.append(finding)
        return findings

    @staticmethod
    def _sort(findings: list[dict]) -> list[dict]:
        return sorted(
            findings,
            key=lambda f: (-SEVERITY_ORDER.get(f["severity"], 0), f["finding_id"]),
        )

    def build_report(self, target: str, findings: list[dict], mode: str) -> dict:
        severity = Counter(f["severity"] for f in findings)
        jurisdictions = Counter()
        for finding in findings:
            for name in finding["jurisdictions"]:
                jurisdictions[name] += 1
        controls_hit = sorted({f["control_id"] for f in findings})
        if severity["critical"] or severity["high"]:
            gate = "BLOCK_DEPLOYMENT"
        elif severity["medium"]:
            gate = "MANUAL_REVIEW"
        else:
            gate = "PASS"
        themes_hit = sorted({f["theme"] for f in findings})
        return {
            "report_schema": "lexaudit.report/v0.1",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "target": target,
            "mode": mode,
            "gate_decision": gate,
            "summary": {
                "findings_total": len(findings),
                "by_severity": dict(severity),
                "by_jurisdiction": dict(jurisdictions),
                "controls_triggered": controls_hit,
                "themes_triggered": themes_hit,
                "controls_available": len(self.controls),
            },
            "findings": findings,
        }


def render_markdown(report: dict) -> str:
    summary = report["summary"]
    lines = [
        f'# Compliance audit: `{report["target"]}`',
        "",
        f'- Generated: {report["generated_at"]}',
        f'- Mode: `{report["mode"]}`',
        f'- Pre-deployment gate: **{report["gate_decision"]}**',
        f'- Findings: **{summary["findings_total"]}**',
        "",
        "## Severity distribution",
        "",
        "| Severity | Count |",
        "| --- | ---: |",
    ]
    for level in ("critical", "high", "medium", "low"):
        count = summary["by_severity"].get(level, 0)
        if count:
            lines.append(f"| {level} | {count} |")
    lines += [
        "",
        "## Jurisdictions implicated by findings",
        "",
        "| Regime | Findings |",
        "| --- | ---: |",
    ]
    for name, count in sorted(summary["by_jurisdiction"].items()):
        lines.append(f"| {name} | {count} |")
    lines += ["", "## Findings", ""]
    if not report["findings"]:
        lines.append("No control violations detected by the prototype rule set.")
    for finding in report["findings"]:
        location = finding["location"]
        where = (
            f'{location.get("file")}:{location.get("line")}'
            if location.get("file")
            else "repository scope"
        )
        lines += [
            f'### {finding["finding_id"]} - {finding["control_title"]}',
            "",
            f'- Control: `{finding["control_id"]}` (theme `{finding["theme"]}`)',
            f'- Severity: **{finding["severity"]}**',
            f'- Location: `{where}`',
            f'- Regimes: {", ".join(finding["jurisdictions"])}',
            f'- Issue: {finding["message"]}',
            "",
            "Evidence:",
            "",
            "```text",
            finding["evidence"],
            "```",
            "",
            "Citations:",
            "",
        ]
        for citation in finding["citations"]:
            lines.append(
                f'- {citation["citation"]} - {citation["title"]} '
                f'(verified: {citation["verified"]})'
            )
            lines.append(f'  > {citation["excerpt"][:220]}...')
        lines += ["", f'Remediation: {finding["remediation"]}', ""]
    return "\n".join(lines) + "\n"


def audit_path(root: Path, mode: str, engine: AuditEngine, name: str) -> dict:
    findings = (
        engine.audit_trace(root) if mode == "trace" else engine.audit_codebase(root)
    )
    report = engine.build_report(name, findings, mode)
    RESULTS.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", name).strip("_").lower()
    (RESULTS / f"{slug}.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (RESULTS / f"{slug}.md").write_text(render_markdown(report), encoding="utf-8")
    return report


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: audit_engine.py <code|trace> <path> [name]", file=sys.stderr)
        return 2
    mode, raw_path = argv[1], Path(argv[2])
    name = argv[3] if len(argv) > 3 else raw_path.name
    controls = json.loads((KG_DIR / "control_index.json").read_text(encoding="utf-8"))
    provisions = json.loads(
        (ROOT / "data" / "processed" / "all_provisions.json").read_text(encoding="utf-8")
    )
    engine = AuditEngine(controls, provisions)
    report = audit_path(raw_path, mode, engine, name)
    print(
        f'{name}: {report["summary"]["findings_total"]} findings, '
        f'gate={report["gate_decision"]}'
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
