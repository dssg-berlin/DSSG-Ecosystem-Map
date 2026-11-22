import json
from datetime import datetime, timezone
from pathlib import Path

from engine import OUTPUTS, ChatEngine, export_artifacts

SCENARIOS = [
    {
        "id": "india_farmer",
        "language": "en",
        "turns": [
            "I am a small farmer in India, aged 42",
            "yes",
            "show me eligible schemes",
        ],
    },
    {
        "id": "germany_family",
        "language": "en",
        "turns": [
            "We live in Germany and have two children under 25",
            "show me schemes",
        ],
    },
    {
        "id": "india_widow_bpl",
        "language": "hi",
        "turns": [
            "मैं 45 साल की विधवा हूँ और मेरे पास बीपीएल कार्ड है",
            "हाँ",
            "योजनाएँ दिखाएँ",
        ],
    },
    {
        "id": "health_emergency",
        "language": "en",
        "turns": [
            "I am in India and my family needs hospital treatment",
            "yes",
            "show schemes",
        ],
    },
    {
        "id": "documents_query",
        "language": "en",
        "turns": [
            "What documents are needed for PM-KISAN?",
        ],
    },
]


def run_scenario(engine, scenario):
    profile = {}
    expecting = None
    asked = 0
    turns = []
    for message in scenario["turns"]:
        result = engine.answer(
            message=message,
            lang=scenario["language"],
            profile=profile,
            expecting=expecting,
            asked=asked,
        )
        profile = result["profile"]
        expecting = result["expecting"]
        asked = profile.get("_asked", 0)
        turns.append({
            "user": message,
            "assistant": result["reply"],
            "expecting": expecting,
            "matches": result["matches"],
            "profile": {key: value for key, value in profile.items() if not key.startswith("_")},
            "sources": result["sources"],
            "graph_edges": len(result["graph"]),
        })
    return {
        "id": scenario["id"],
        "language": scenario["language"],
        "turns": turns,
        "final_profile": profile,
        "final_matches": turns[-1]["matches"],
    }


def main():
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    engine = ChatEngine()
    results = [run_scenario(engine, scenario) for scenario in SCENARIOS]
    graph_path, turtle_path = export_artifacts(engine)
    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "scenario_count": len(results),
        "scheme_count": len(engine.kb.schemes),
        "source_count": len(engine.kb.sources),
        "graph_nodes": engine.kb.graph.number_of_nodes(),
        "graph_edges": engine.kb.graph.number_of_edges(),
        "exports": [str(graph_path), str(turtle_path)],
        "scenarios": results,
    }
    (OUTPUTS / "demo_results.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = ["# Demo transcript", "", f"Generated: {payload['generated_at_utc']}", ""]
    for result in results:
        lines.extend([f"## {result['id']}", "", f"Language: {result['language']}", ""])
        for index, turn in enumerate(result["turns"], start=1):
            lines.extend([
                f"### Turn {index}", "",
                f"**User:** {turn['user']}", "",
                "**Assistant:**", "",
                turn["assistant"], "",
                f"Matches: {', '.join(turn['matches']) or 'none'}  ",
                f"Expecting: {turn['expecting'] or 'nothing'}  ",
                f"Sources: {', '.join(turn['sources']) or 'none'}", "",
            ])
        lines.append("---")
        lines.append("")
    (OUTPUTS / "demo_transcript.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({
        "status": "ok",
        "scenarios": len(results),
        "matches": {item["id"]: item["final_matches"] for item in results},
        "outputs": [str(OUTPUTS / "demo_results.json"), str(OUTPUTS / "demo_transcript.md"), str(graph_path), str(turtle_path)],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
