from __future__ import annotations

import logging

from flask import Flask, jsonify, request
from flask_cors import CORS

from config import load_config
from retrieval.generator import answer

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

cfg = load_config()
app = Flask(__name__)
app.secret_key = cfg.flask_secret_key or "dev-insecure-change-me"

# CORS: restrict /api/* to the internal Wiki.js origin only (SEC-008)
CORS(app, resources={r"/api/*": {"origins": cfg.wikijs_base_url or "*"}})


@app.get("/api/health")
def health():
    return jsonify({"status": "ok"})


@app.post("/api/ask")
def ask():
    body = request.get_json(silent=True) or {}
    question = (body.get("question") or "").strip()

    if not question:
        return jsonify({"error": "question is required"}), 400

    try:
        result = answer(question)
        return jsonify({"answer": result.text, "citations": result.citations})
    except Exception as e:
        logger.exception("Error answering question")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5057, debug=False)
