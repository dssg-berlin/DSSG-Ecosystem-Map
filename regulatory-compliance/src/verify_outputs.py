from __future__ import annotations

import json
import sys
from pathlib import Path

import networkx as nx

ROOT = Path(__file__).resolve().parents[1]
checks = []


def check(name: str, condition: bool, detail: str = "") -> None:
    checks.append((name, condition, detail))


manifest = json.loads((ROOT / "data/processed/manifest.json").read_text())
check("three official sources collected", len(manifest["sources"]) == 3)
provisions = json.loads((ROOT / "data/processed/all_provisions.json").read_text())
check("255 provisions parsed", len(provisions) == 255, str(len(provisions)))
check(
    "all citations verified",
    all(p["citation_verified"] for p in provisions),
    f'{sum(p["citation_verified"] for p in provisions)}/{len(provisions)}',
)
check(
    "source snapshots recorded",
    all(Path(ROOT / s["raw_file"]).exists() for s in manifest["sources"].values()),
)
summary = json.loads((ROOT / "data/knowledge_graph/graph_summary.json").read_text())
check("graph validation clean", not summary["validation_errors"])
graph = nx.read_graphml(ROOT / "data/knowledge_graph/graph.graphml")
check(
    "graphml loads with expected size",
    graph.number_of_nodes() == summary["graph_nodes"]
    and graph.number_of_edges() == summary["graph_edges"],
    f'{graph.number_of_nodes()} nodes / {graph.number_of_edges()} edges',
)
controls = json.loads((ROOT / "data/knowledge_graph/control_index.json").read_text())
check("25 controls indexed", len(controls) == 25)
check(
    "control citations resolve and verify",
    all(
        c["resolved_citations"] and all(r["verified"] for r in c["resolved_citations"])
        for c in controls
    ),
)
expected = {
    "vulnerable_app": "BLOCK_DEPLOYMENT",
    "compliant_app": "PASS",
    "risky_agent": "BLOCK_DEPLOYMENT",
    "clean_agent": "PASS",
}
for name, gate in expected.items():
    json_path = ROOT / "results" / "audits" / f"{name}.json"
    md_path = ROOT / "results" / "audits" / f"{name}.md"
    check(f"{name} report exists", json_path.exists() and md_path.exists())
    if json_path.exists():
        report = json.loads(json_path.read_text())
        check(f"{name} gate decision", report["gate_decision"] == gate, report["gate_decision"])
        check(
            f"{name} citations verified",
            all(c["verified"] for f in report["findings"] for c in f["citations"]),
        )
pipeline = json.loads((ROOT / "results/pipeline_summary.json").read_text())
check("pipeline summary present", len(pipeline["audits"]) == 4)

failed = [c for c in checks if not c[1]]
for name, ok, detail in checks:
    print(f'{"PASS" if ok else "FAIL"}  {name}{(" | " + detail) if detail else ""}')
print(f"\n{len(checks) - len(failed)}/{len(checks)} checks passed")
sys.exit(1 if failed else 0)
