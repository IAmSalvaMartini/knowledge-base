from __future__ import annotations

import logging

import chromadb

from config import load_config
from ingest.models import Chunk

logger = logging.getLogger(__name__)

_collection = None


def _get_collection() -> chromadb.Collection:
    global _collection
    if _collection is None:
        cfg = load_config()
        cfg.chroma_path.mkdir(parents=True, exist_ok=True)
        client = chromadb.PersistentClient(path=str(cfg.chroma_path))
        _collection = client.get_or_create_collection(
            name="kb_chunks",
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


def upsert(chunks: list[Chunk], embeddings: list[list[float]]) -> None:
    col = _get_collection()
    col.upsert(
        ids=[c.chunk_id for c in chunks],
        embeddings=embeddings,
        documents=[c.text for c in chunks],
        metadatas=[{
            "page_path": c.page_path,
            "title": c.title,
            "heading_path": c.heading_path,
        } for c in chunks],
    )
    logger.info("Upserted %d chunks", len(chunks))


def delete_by_page(page_path: str) -> None:
    col = _get_collection()
    col.delete(where={"page_path": page_path})
    logger.info("Deleted chunks for page: %s", page_path)


def get_page_hash(page_path: str) -> str | None:
    """Return stored sha256 for a page, or None if not found."""
    col = _get_collection()
    results = col.get(where={"page_path": page_path}, limit=1, include=["metadatas"])
    if results["ids"]:
        return results["metadatas"][0].get("sha256")
    return None


def upsert_with_hash(chunks: list[Chunk], embeddings: list[list[float]], sha256: str) -> None:
    """Upsert chunks carrying the page sha256 in metadata for incremental tracking."""
    col = _get_collection()
    col.upsert(
        ids=[c.chunk_id for c in chunks],
        embeddings=embeddings,
        documents=[c.text for c in chunks],
        metadatas=[{
            "page_path": c.page_path,
            "title": c.title,
            "heading_path": c.heading_path,
            "sha256": sha256,
        } for c in chunks],
    )
    logger.info("Upserted %d chunks (page_path=%s)", len(chunks), chunks[0].page_path if chunks else "?")


def query(embedding: list[float], top_k: int) -> list[dict]:
    """Return top_k chunks as dicts with text, metadata, and distance."""
    col = _get_collection()
    results = col.query(
        query_embeddings=[embedding],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )
    output = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        output.append({"text": doc, "metadata": meta, "distance": dist})
    return output
