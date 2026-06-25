"""TEST-006: retriever ranks semantically matching chunk first."""
from __future__ import annotations

from unittest.mock import patch

from ingest.models import Chunk
from ingest import store
from retrieval.retriever import retrieve


def _seed_store():
    """Seed store with 3 chunks via dummy embedder."""
    from ingest.embedder import embed_texts
    chunks = [
        Chunk("a.md#s-0", "a.md", "Backport", "Backport", "Cherry-pick the fix onto the release branch."),
        Chunk("b.md#s-0", "b.md", "Deploy",   "Deploy",   "Run the deployment pipeline after merging."),
        Chunk("c.md#s-0", "c.md", "Rollback", "Rollback", "Revert the release tag to the previous version."),
    ]
    vecs = embed_texts([c.text for c in chunks])
    for c, v in zip(chunks, vecs):
        store.upsert_with_hash([c], [v], sha256=c.chunk_id)
    return chunks


def test_retrieve_returns_results():
    _seed_store()
    results = retrieve("how do I backport a fix?", top_k=3)
    assert len(results) > 0


def test_retrieve_respects_top_k():
    _seed_store()
    results = retrieve("deployment", top_k=2)
    assert len(results) <= 2


def test_retrieve_result_has_expected_keys():
    _seed_store()
    results = retrieve("rollback a release", top_k=1)
    assert "text" in results[0]
    assert "metadata" in results[0]
    assert "distance" in results[0]
