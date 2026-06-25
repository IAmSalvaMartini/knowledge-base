from __future__ import annotations

import logging
import time
from typing import Protocol

from config import load_config

logger = logging.getLogger(__name__)


# ── Backend protocol ──────────────────────────────────────────────────────────

class EmbedBackend(Protocol):
    def embed_texts(self, texts: list[str]) -> list[list[float]]: ...


# ── Ollama backend ────────────────────────────────────────────────────────────

class OllamaBackend:
    def __init__(self, host: str, model: str) -> None:
        import ollama
        self._client = ollama.Client(host=host)
        self._model = model

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        embeddings: list[list[float]] = []
        dim: int | None = None
        for i, text in enumerate(texts):
            for attempt in range(4):
                try:
                    resp = self._client.embeddings(model=self._model, prompt=text)
                    vec = resp["embedding"]
                    if dim is None:
                        dim = len(vec)
                    elif len(vec) != dim:
                        raise ValueError(f"Dimension mismatch at index {i}")
                    embeddings.append(vec)
                    break
                except Exception as e:
                    logger.warning("Ollama error (attempt %d/4): %s", attempt + 1, e)
                    time.sleep(2 ** attempt)
            else:
                raise RuntimeError(f"Failed to embed text at index {i} after 4 attempts")
        return embeddings


# ── sentence-transformers backend ─────────────────────────────────────────────

class SentenceTransformersBackend:
    # Default model: small, fast, 384-dim, ~90 MB download.
    # Set KB_EMBED_MODEL to any SBERT-compatible model name.
    DEFAULT_MODEL = "all-MiniLM-L6-v2"

    def __init__(self, model: str) -> None:
        from sentence_transformers import SentenceTransformer
        effective = model if model != "nomic-embed-text" else self.DEFAULT_MODEL
        logger.info("Loading sentence-transformers model: %s", effective)
        self._model = SentenceTransformer(effective)

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        vecs = self._model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
        return [v.tolist() for v in vecs]


# ── Dummy backend (pipeline smoke-testing) ────────────────────────────────────

class DummyBackend:
    DIM = 384

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        import random
        logger.warning("DummyBackend: returning random vectors — retrieval quality is meaningless")
        return [[random.random() for _ in range(self.DIM)] for _ in texts]


# ── Factory & public API ──────────────────────────────────────────────────────

_backend: EmbedBackend | None = None


def _get_backend() -> EmbedBackend:
    global _backend
    if _backend is None:
        cfg = load_config()
        name = cfg.embed_backend.lower()
        if name == "ollama":
            _backend = OllamaBackend(host=cfg.ollama_host, model=cfg.embed_model)
        elif name == "sentence_transformers":
            _backend = SentenceTransformersBackend(model=cfg.embed_model)
        elif name == "dummy":
            _backend = DummyBackend()
        else:
            raise ValueError(
                f"Unknown KB_EMBED_BACKEND: {cfg.embed_backend!r}. "
                "Choices: ollama | sentence_transformers | dummy"
            )
    return _backend


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a list of texts. Backend selected by KB_EMBED_BACKEND env var."""
    return _get_backend().embed_texts(texts)
