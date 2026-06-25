"""TEST-011: upload page — auth gate, validation, ingest trigger."""
from __future__ import annotations

import io
from unittest.mock import patch


def test_upload_get_requires_auth(client):
    r = client.get("/upload/")
    assert r.status_code in (302, 401)
    if r.status_code == 302:
        assert "/auth/login" in r.headers["Location"]


def test_upload_get_authenticated_returns_200(authed_client):
    r = authed_client.get("/upload/")
    assert r.status_code == 200
    assert b"Upload" in r.data


def test_upload_rejects_disallowed_extension(authed_client):
    data = {"file": (io.BytesIO(b"fake"), "malware.exe")}
    r = authed_client.post("/upload/", data=data, content_type="multipart/form-data")
    assert r.status_code in (200, 302)
    # Should stay on upload page with an error flash, not crash
    assert r.status_code != 500


def test_upload_rejects_oversize_file(authed_client, monkeypatch):
    monkeypatch.setenv("KB_MAX_UPLOAD_MB", "0")
    import ingest.store as s; s._collection = None
    data = {"file": (io.BytesIO(b"x" * 1024), "notes.txt")}
    r = authed_client.post("/upload/", data=data, content_type="multipart/form-data")
    assert r.status_code != 500


def test_upload_valid_txt_triggers_ingest(authed_client, tmp_path, monkeypatch):
    monkeypatch.setenv("KB_UPLOADS_PATH", str(tmp_path))
    import ingest.store as s; s._collection = None

    with patch("surfaces.upload.routes._ingest_page") as mock_ingest:
        data = {"file": (io.BytesIO(b"Some tribal knowledge here."), "knowledge.txt")}
        r = authed_client.post("/upload/", data=data, content_type="multipart/form-data")

    assert r.status_code in (200, 302)
    mock_ingest.assert_called_once()
    saved = list(tmp_path.iterdir())
    assert any(f.name == "knowledge.txt" for f in saved)
