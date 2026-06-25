"""TEST-008: Flask API — /api/ask and /api/health."""
from __future__ import annotations

from unittest.mock import patch

from retrieval.generator import Answer


def test_health_returns_200(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.get_json()["status"] == "ok"


def test_ask_without_auth_returns_401(client):
    r = client.post("/api/ask", json={"question": "hello"})
    assert r.status_code == 401


def test_ask_with_session_returns_answer(authed_client):
    mock_answer = Answer(text="Cherry-pick the commit. [source: backport.md]", citations=["backport.md"])
    with patch("app.answer", return_value=mock_answer):
        r = authed_client.post("/api/ask", json={"question": "how to backport?"})
    assert r.status_code == 200
    data = r.get_json()
    assert "answer" in data
    assert "citations" in data


def test_ask_with_cli_token_returns_answer(client):
    mock_answer = Answer(text="Use cherry-pick. [source: guide.md]", citations=["guide.md"])
    with patch("app.answer", return_value=mock_answer):
        r = client.post(
            "/api/ask",
            json={"question": "backport?"},
            headers={"Authorization": "Bearer test-cli-token"},
        )
    assert r.status_code == 200


def test_ask_missing_question_returns_400(authed_client):
    r = authed_client.post("/api/ask", json={})
    assert r.status_code == 400


def test_ask_empty_question_returns_400(authed_client):
    r = authed_client.post("/api/ask", json={"question": "   "})
    assert r.status_code == 400
