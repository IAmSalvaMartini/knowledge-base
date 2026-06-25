"""TEST-004: store.py"""
from __future__ import annotations

from ingest.models import Chunk
from ingest import store


def _chunk(n: int) -> Chunk:
    return Chunk(
        chunk_id=f"page/test.md#section-{n}",
        page_path="page/test.md",
        title="Test",
        heading_path=f"Test > Section {n}",
        text=f"This is section {n} content.",
    )


def _vec(seed: int, dim: int = 384) -> list[float]:
    import random
    random.seed(seed)
    return [random.random() for _ in range(dim)]


def test_upsert_then_query_returns_chunk():
    c = _chunk(1)
    v = _vec(1)
    store.upsert_with_hash([c], [v], sha256="hash1")
    results = store.query(v, top_k=1)
    assert results
    assert results[0]["metadata"]["page_path"] == "page/test.md"


def test_get_page_hash_round_trips():
    c = _chunk(2)
    store.upsert_with_hash([c], [_vec(2)], sha256="deadbeef")
    assert store.get_page_hash("page/test.md") == "deadbeef"


def test_delete_by_page_removes_all_chunks():
    chunks = [_chunk(i) for i in range(3)]
    vecs = [_vec(i) for i in range(3)]
    store.upsert_with_hash(chunks, vecs, sha256="todelete")
    store.delete_by_page("page/test.md")
    assert store.get_page_hash("page/test.md") is None
    results = store.query(_vec(0), top_k=5)
    assert all(r["metadata"]["page_path"] != "page/test.md" for r in results)


def test_upsert_updates_existing():
    c = _chunk(4)
    store.upsert_with_hash([c], [_vec(4)], sha256="v1")
    assert store.get_page_hash("page/test.md") == "v1"
    store.upsert_with_hash([c], [_vec(4)], sha256="v2")
    assert store.get_page_hash("page/test.md") == "v2"
