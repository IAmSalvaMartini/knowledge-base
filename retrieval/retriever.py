from __future__ import annotations

from config import load_config
from ingest import embedder, store


def retrieve(question: str, top_k: int | None = None) -> list[dict]:
    """Embed question, return top_k chunks with text/metadata/distance."""
    cfg = load_config()
    k = top_k if top_k is not None else cfg.top_k
    vec = embedder.embed_texts([question])[0]
    return store.query(vec, k)
