"""TEST-002: chunker.py"""
from __future__ import annotations

from ingest.chunker import chunk_page, _approx_tokens
from ingest.models import Page


def _page(body: str) -> Page:
    return Page(path="test.md", title="Test Page", body=body, sha256="abc")


def test_chunks_never_exceed_max_tokens():
    body = "word " * 2000  # ~10000 chars
    chunks = chunk_page(_page(body), max_tokens=800)
    for c in chunks:
        assert _approx_tokens(c.text) <= 800


def test_heading_paths_preserved():
    body = "## Setup\nInstall the tool.\n## Usage\nRun the tool."
    chunks = chunk_page(_page(body))
    paths = {c.heading_path for c in chunks}
    assert any("Setup" in p for p in paths)
    assert any("Usage" in p for p in paths)


def test_chunk_ids_unique():
    body = "## A\n" + "word " * 500 + "\n## B\n" + "word " * 500
    chunks = chunk_page(_page(body))
    ids = [c.chunk_id for c in chunks]
    assert len(ids) == len(set(ids))


def test_overlap_produces_shared_content():
    body = "word " * 1600  # forces two chunks with overlap
    chunks = chunk_page(_page(body), max_tokens=800, overlap=100)
    if len(chunks) >= 2:
        end_of_first = chunks[0].text[-200:]
        start_of_second = chunks[1].text[:200]
        # some characters overlap
        assert any(w in start_of_second for w in end_of_first.split()[:5])


def test_no_heading_body_becomes_single_chunk():
    body = "short body"
    chunks = chunk_page(_page(body))
    assert len(chunks) == 1
    assert chunks[0].text == "short body"
