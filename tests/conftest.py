"""Shared fixtures for the knowledge base test suite."""
from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Force dummy embedder and temp paths before any app import
os.environ["KB_EMBED_BACKEND"] = "dummy"
os.environ["KB_LLM_PROVIDER"] = "anthropic"
os.environ["KB_ANSWER_MODEL"] = "claude-haiku-4-5-20251001"
os.environ["KB_ESCALATION_MODEL"] = "claude-sonnet-4-6"
os.environ["KB_FLASK_SECRET_KEY"] = "test-secret"
os.environ["KB_WIKIJS_BASE_URL"] = "http://wiki.test"
os.environ["KB_CLI_TOKEN"] = "test-cli-token"
os.environ["KB_TOP_K"] = "3"


@pytest.fixture(autouse=True)
def temp_data_dirs(tmp_path, monkeypatch):
    """Redirect chroma and uploads to temp dirs for every test."""
    chroma = tmp_path / "chroma"
    uploads = tmp_path / "uploads"
    chroma.mkdir()
    uploads.mkdir()
    monkeypatch.setenv("KB_CHROMA_PATH", str(chroma))
    monkeypatch.setenv("KB_UPLOADS_PATH", str(uploads))

    # Reset cached singletons so each test gets fresh store/embedder
    import ingest.store as store_mod
    import ingest.embedder as embedder_mod
    store_mod._collection = None
    embedder_mod._backend = None

    yield tmp_path


@pytest.fixture()
def app():
    from app import app as flask_app
    flask_app.config["TESTING"] = True
    flask_app.config["WTF_CSRF_ENABLED"] = False
    return flask_app


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def authed_client(app):
    """Test client with a fake SSO session injected."""
    with app.test_client() as c:
        with c.session_transaction() as sess:
            sess["user"] = {"email": "test@example.com", "name": "Test User"}
        yield c
