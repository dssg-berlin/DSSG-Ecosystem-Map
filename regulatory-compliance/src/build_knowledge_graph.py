from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import networkx as nx
import yaml

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
OUT = ROOT / "data" / "knowledge_graph"
DOCS = ROOT / "docs"

SOURCE_FILES = {
    "GDPR": "gdpr_source_normalized.txt",
    "EU AI Act": "ai_act_source_normalized.txt",
    "India DPDP Act": "dpdp_source_normalized.txt",
}


def load_json(name: str):
    return json.loads((PROCESSED / name).read_text(encoding="utf-8"))


def build() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    DOCS.mkdir(parents=True, exist_ok=True)
    provisions = load_json("all_provisions.json")
    ontology = yaml.safe_load((ROOT / "config" / "ontology.yaml").read_text(encoding="utf-8"))
    by_id = {p["provision_id"]: p for p in provisions}
    normalized_sources = {
        instrument: (PROCESSED / filename).read_text(encoding="utf-8")
        for instrument, filename in SOURCE_FILES.items()
    }

    errors = []
    for provision in provisions:
        corpus = normalized_sources[provision["instrument"]]
        provision["citation_verified"] = provision["excerpt"] in corpus
        if not provision["citation_verified"]:
            errors.append(f"excerpt not found in source: {provision['provision_id']}")

    theme_ids = {t["id"] for t in ontology["themes"]}
    control_ids = {c["id"] for c in ontology["controls"]}
    for theme in ontology["themes"]:
        for citation in theme["provisions"]:
            if citation not in by_id:
                errors.append(f"unknown citation {citation} in theme {theme['id']}")
        for left, right, _relation in theme["mappings"]:
            for citation in (left, right):
                if citation not in by_id:
                    errors.append(f"unknown mapping citation {citation} in theme {theme['id']}")
    for control in ontology["controls"]:
        if control["theme"] not in theme_ids:
            errors.append(f"unknown theme {control['theme']} in control {control['id']}")
        for citation in control["citations"]:
            if citation not in by_id:
                errors.append(f"unknown citation {citation} in control {control['id']}")
    if errors:
        raise ValueError("ontology validation failed:\n" + "\n".join(errors))

    graph = nx.DiGraph()
    instruments = ["GDPR", "EU AI Act", "India DPDP Act"]
    for instrument in instruments:
        graph.add_node(
            f"instrument:{instrument}",
            node_type="instrument",
            label=instrument,
            provisions=sum(1 for p in provisions if p["instrument"] == instrument),
        )
    for provision in provisions:
        graph.add_node(
            f"provision:{provision['provision_id']}",
            node_type="provision",
            label=f"{provision['instrument']} {provision['unit']} {provision['number']}",
            citation=provision["citation"],
            title=provision["title"],
            instrument=provision["instrument"],
            citation_verified=provision["citation_verified"],
            source_sha256=provision["source_sha256"],
        )
        graph.add_edge(
            f"instrument:{provision['instrument']}",
            f"provision:{provision['provision_id']}",
            relation="CONTAINS",
        )
    for theme in ontology["themes"]:
        graph.add_node(
            f"theme:{theme['id']}",
            node_type="theme",
            label=theme["label"],
            slug=theme["slug"],
            description=" ".join(theme["description"].split()),
        )
        for citation in theme["provisions"]:
            graph.add_edge(
                f"theme:{theme['id']}", f"provision:{citation}", relation="MAPS_TO"
            )
        for left, right, relation in theme["mappings"]:
            graph.add_edge(
                f"provision:{left}", f"provision:{right}", relation=relation.upper()
            )
    for control in ontology["controls"]:
        graph.add_node(
            f"control:{control['id']}",
            node_type="control",
            label=control["title"],
            severity=control["severity"],
            rationale=" ".join(control["rationale"].split()),
        )
        graph.add_edge(
            f"theme:{control['theme']}", f"control:{control['id']}", relation="ENFORCED_BY"
        )
        for citation in control["citations"]:
            graph.add_edge(
                f"control:{control['id']}", f"provision:{citation}", relation="CITES"
            )

    nodes = []
    for node_id, attrs in graph.nodes(data=True):
        nodes.append({"id": node_id, **attrs})
    edges = []
    for source, target, attrs in graph.edges(data=True):
        edges.append({"source": source, "target": target, **attrs})
    graph_json = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "directed": True,
        "node_count": graph.number_of_nodes(),
        "edge_count": graph.number_of_edges(),
        "nodes": nodes,
        "edges": edges,
    }
    (OUT / "graph.json").write_text(
        json.dumps(graph_json, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    nx.write_graphml(graph, OUT / "graph.graphml")

    theme_instruments = {}
    for theme in ontology["themes"]:
        theme_instruments[theme["id"]] = sorted(
            {by_id[c]["instrument"] for c in theme["provisions"]}
        )
    overlap_counts = Counter()
    for instruments_for_theme in theme_instruments.values():
        for i, left in enumerate(instruments_for_theme):
            for right in instruments_for_theme[i + 1 :]:
                overlap_counts[tuple(sorted((left, right)))] += 1

    citations_per_theme = {
        theme["id"]: len(theme["provisions"]) for theme in ontology["themes"]
    }
    control_severity = Counter(c["severity"] for c in ontology["controls"])
    summary = {
        "generated_at": graph_json["generated_at"],
        "instruments": {
            instrument: sum(1 for p in provisions if p["instrument"] == instrument)
            for instrument in instruments
        },
        "provisions_total": len(provisions),
        "citation_verified_total": sum(
            1 for p in provisions if p["citation_verified"]
        ),
        "themes_total": len(ontology["themes"]),
        "controls_total": len(ontology["controls"]),
        "control_severity": dict(control_severity),
        "themes_covering_all_three_regimes": sum(
            1 for values in theme_instruments.values() if len(values) == 3
        ),
        "pairwise_theme_overlap": {
            " x ".join(pair): count for pair, count in sorted(overlap_counts.items())
        },
        "citation_density_per_theme": citations_per_theme,
        "graph_nodes": graph.number_of_nodes(),
        "graph_edges": graph.number_of_edges(),
        "validation_errors": errors,
    }
    (OUT / "graph_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )

    control_index = []
    for control in ontology["controls"]:
        resolved = []
        for citation in control["citations"]:
            provision = by_id[citation]
            resolved.append(
                {
                    "provision_id": citation,
                    "citation": provision["citation"],
                    "title": provision["title"],
                    "excerpt": provision["excerpt"],
                    "source_url": provision["source_url"],
                    "source_sha256": provision["source_sha256"],
                    "verified": provision["citation_verified"],
                }
            )
        control_index.append({**control, "resolved_citations": resolved})
    (OUT / "control_index.json").write_text(
        json.dumps(control_index, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    lines = [
        "# Cross-law citation crosswalk",
        "",
        "Generated by `src/build_knowledge_graph.py`. Citations were verified by",
        "checking each stored excerpt against the normalized official source text.",
        "",
        "| Theme | GDPR | EU AI Act | DPDP Act | Controls |",
        "| --- | --- | --- | --- | --- |",
    ]
    theme_controls = defaultdict(list)
    for control in ontology["controls"]:
        theme_controls[control["theme"]].append(control["id"])
    for theme in ontology["themes"]:
        refs = defaultdict(list)
        for citation in theme["provisions"]:
            provision = by_id[citation]
            refs[provision["instrument"]].append(
                provision["unit"][0] + provision["number"]
            )
        lines.append(
            "| {label} | {gdpr} | {ai} | {dpdp} | {controls} |".format(
                label=f'{theme["id"]} {theme["label"]}',
                gdpr=", ".join(refs["GDPR"]) or "-",
                ai=", ".join(refs["EU AI Act"]) or "-",
                dpdp=", ".join(refs["India DPDP Act"]) or "-",
                controls=", ".join(theme_controls[theme["id"]]) or "-",
            )
        )
    lines += [
        "",
        "## Pairwise theme overlap",
        "",
        "| Regime pair | Shared themes |",
        "| --- | ---: |",
    ]
    for pair, count in sorted(overlap_counts.items()):
        lines.append(f"| {pair[0]} x {pair[1]} | {count} |")
    lines.append("")
    (DOCS / "crosswalk.md").write_text("\n".join(lines), encoding="utf-8")

    print(
        f"graph: {graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges, "
        f"{summary['citation_verified_total']}/{len(provisions)} citations verified"
    )
    return 0


if __name__ == "__main__":
    sys.exit(build())
