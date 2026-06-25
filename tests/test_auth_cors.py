"""TEST-012: auth gate and CORS on /api/ask."""
from __future__ import annotations

from unittest.mock import patch

from retrieval.generator import Answer


def test_unauthenticated_ask_rejected(client):
    r = client.post("/api/ask", json={"question": "test"})
    assert r.status_code == 401


def test_wrong_cli_token_rejected(client):
    r = client.post(
        "/api/ask",
        json={"question": "test"},
        headers={"Authorization": "Bearer wrong-token"},
    )
    assert r.status_code == 401


def test_cors_preflight_allows_wikijs_origin(client):
    r = client.options(
        "/api/ask",
        headers={
            "Origin": "http://wiki.test",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert r.status_code in (200, 204)
    assert "http://wiki.test" in r.headers.get("Access-Control-Allow-Origin", "")


def test_cors_preflight_blocks_unknown_origin(client):
    r = client.options(
        "/api/ask",
        headers={
            "Origin": "https://evil.example.com",
            "Access-Control-Request-Method": "POST",
        },
    )
    origin = r.headers.get("Access-Control-Allow-Origin", "")
    assert "evil.example.com" not in origin
