from __future__ import annotations

import logging

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

from auth.oidc import bp as auth_bp, has_valid_token, init_auth, login_required
from config import load_config
from retrieval.generator import answer
from surfaces.upload.routes import bp as upload_bp

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

cfg = load_config()
app = Flask(__name__)
app.secret_key = cfg.flask_secret_key or "dev-insecure-change-me"

# CORS: restrict /api/* to the internal Wiki.js origin only (SEC-008)
CORS(app, resources={r"/api/*": {"origins": cfg.wikijs_base_url or "*"}})

# Blueprints
init_auth(app)
app.register_blueprint(auth_bp)
app.register_blueprint(upload_bp)


@app.get("/api/health")
def health():
    return jsonify({"status": "ok"})


@app.post("/api/ask")
def ask():
    # Allow authenticated session (browser) OR valid CLI service token
    from flask import session
    if "user" not in session and not has_valid_token():
        return jsonify({"error": "Unauthorized"}), 401

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


@app.get("/static/widget/ask-widget.js")
def serve_widget():
    """Serve the embeddable Wiki.js chat widget."""
    return send_from_directory("surfaces/widget", "ask-widget.js", mimetype="application/javascript")


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5057, debug=False)
