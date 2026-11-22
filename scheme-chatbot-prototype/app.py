import os

from flask import Flask, jsonify, request, send_from_directory

from engine import OUTPUTS, ChatEngine, export_artifacts

app = Flask(__name__, static_folder="static")
app.json.ensure_ascii = False
engine = ChatEngine()


@app.get("/")
def index():
    return send_from_directory("static", "index.html")


@app.get("/api/health")
def health():
    return jsonify({
        "status": "ok",
        "schemes": len(engine.kb.schemes),
        "sources": len(engine.kb.sources),
        "fields": len(engine.kb.fields),
        "graph_nodes": engine.kb.graph.number_of_nodes(),
        "graph_edges": engine.kb.graph.number_of_edges(),
    })


@app.get("/api/schemes")
def schemes():
    lang = request.args.get("language", "en")
    return jsonify([
        {
            "id": scheme["id"],
            "name": scheme["name"].get(lang, scheme["name"]["en"]),
            "country": scheme["country"],
            "need": scheme["need"],
            "benefit": scheme["benefit"].get(lang, scheme["benefit"]["en"]) if isinstance(scheme["benefit"], dict) else scheme["benefit"],
            "sources": scheme["sources"],
        }
        for scheme in engine.kb.schemes
    ])


@app.get("/api/schemes/<scheme_id>")
def scheme_detail(scheme_id):
    if scheme_id not in engine.kb.by_id:
        return jsonify({"error": "unknown scheme", "id": scheme_id}), 404
    lang = request.args.get("language", "en")
    return jsonify({
        "id": scheme_id,
        "detail": engine.format_detail(scheme_id, lang),
        "graph": engine.kb.neighbors(scheme_id),
    })


@app.post("/api/chat")
def chat():
    payload = request.get_json(silent=True) or {}
    result = engine.answer(
        message=payload.get("message", ""),
        lang=payload.get("language", "en"),
        profile=payload.get("profile"),
        expecting=payload.get("expecting"),
        asked=payload.get("asked", 0),
    )
    result["api_version"] = "1.0"
    return jsonify(result)


@app.post("/api/export")
def export():
    graph_path, turtle_path = export_artifacts(engine)
    return jsonify({
        "knowledge_graph": str(graph_path),
        "turtle": str(turtle_path),
        "exists": graph_path.exists() and turtle_path.exists(),
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "7860"))
    app.run(host="0.0.0.0", port=port, debug=False)
