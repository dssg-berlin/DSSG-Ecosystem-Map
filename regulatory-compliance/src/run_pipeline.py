from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import collect_sources
import build_knowledge_graph
from audit_engine import AuditEngine, audit_path

TARGETS = [
    ("code", "examples/vulnerable_app", "vulnerable_app"),
    ("code", "examples/compliant_app", "compliant_app"),
    ("trace", "examples/agent_traces/risky_agent.jsonl", "risky_agent"),
    ("trace", "examples/agent_traces/clean_agent.jsonl", "clean_agent"),
]


def main(argv: list[str]) -> int:
    skip_fetch = "--skip-fetch" in argv
    started = datetime.now(timezone.utc)
    if not skip_fetch:
        collect_sources.main()
    else:
        print("collection: using cached source snapshots")
    build_knowledge_graph.build()

    controls = json.loads(
        (ROOT / "data" / "knowledge_graph" / "control_index.json").read_text(encoding="utf-8")
    )
    provisions = json.loads(
        (ROOT / "data" / "processed" / "all_provisions.json").read_text(encoding="utf-8")
    )
    engine = AuditEngine(controls, provisions)
    reports = []
    for mode, relative_path, name in TARGETS:
        report = audit_path(ROOT / relative_path, mode, engine, name)
        reports.append(
            {
                "target": name,
                "mode": mode,
                "gate_decision": report["gate_decision"],
                "findings": report["summary"]["findings_total"],
                "by_severity": report["summary"]["by_severity"],
                "by_jurisdiction": report["summary"]["by_jurisdiction"],
                "controls_triggered": report["summary"]["controls_triggered"],
                "report_json": f"results/audits/{name}.json",
                "report_md": f"results/audits/{name}.md",
            }
        )
        print(f"audit {name}: {report['summary']['findings_total']} findings, {report['gate_decision']}")

    summary = {
        "pipeline": "lexaudit prototype",
        "version": "0.1.0",
        "started_at": started.isoformat(),
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "skip_fetch": skip_fetch,
        "graph_summary": json.loads(
            (ROOT / "data" / "knowledge_graph" / "graph_summary.json").read_text(encoding="utf-8")
        ),
        "audits": reports,
    }
    (ROOT / "results" / "pipeline_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    print("pipeline complete: results/pipeline_summary.json")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
