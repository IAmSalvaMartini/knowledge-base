"""TEST-005: incremental ingest — no re-embedding on unchanged content."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from ingest.run import run


def _make_mirror(tmp_path: Path) -> Path:
    mirror = tmp_path / "mirror"
    mirror.mkdir()
    (mirror / "page.md").write_text("# Guide\nSome content.", encoding="utf-8")
    return mirror


def test_second_run_skips_embedding(tmp_path, monkeypatch):
    mirror = _make_mirror(tmp_path)
    monkeypatch.setenv("KB_CONTENT_MIRROR_PATH", str(mirror))

    call_counts = {"n": 0}
    original_embed = __import__("ingest.embedder", fromlist=["embed_texts"]).embed_texts

    def counting_embed(texts):
        call_counts["n"] += len(texts)
        return original_embed(texts)

    with patch("ingest.embedder.embed_texts", side_effect=counting_embed):
        run()
        first_count = call_counts["n"]
        assert first_count > 0, "First run should embed something"

        call_counts["n"] = 0
        run()
        assert call_counts["n"] == 0, "Second run must not re-embed unchanged pages"


def test_changed_page_re_embeds(tmp_path, monkeypatch):
    mirror = _make_mirror(tmp_path)
    monkeypatch.setenv("KB_CONTENT_MIRROR_PATH", str(mirror))

    with patch("ingest.run._pull_mirror"):
        run()
        (mirror / "page.md").write_text("# Guide\nUpdated content.", encoding="utf-8")

        call_counts = {"n": 0}
        original_embed = __import__("ingest.embedder", fromlist=["embed_texts"]).embed_texts

        def counting_embed(texts):
            call_counts["n"] += len(texts)
            return original_embed(texts)

        with patch("ingest.embedder.embed_texts", side_effect=counting_embed):
            run()
            assert call_counts["n"] > 0, "Changed page must be re-embedded"
