from __future__ import annotations

import logging
import time

import ollama

from config import load_config

logger = logging.getLogger(__name__)

_cfg = None


def _config():
    global _cfg
    if _cfg is None:
        _cfg = load_config()
    return _cfg


def _client() -> ollama.Client:
    return ollama.Client(host=_config().ollama_host)


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a list of texts via local Ollama. Returns one vector per input."""
    cfg = _config()
    client = _client()
    embeddings: list[list[float]] = []
    dim: int | None = None

    for i, text in enumerate(texts):
        for attempt in range(4):
            try:
                resp = client.embeddings(model=cfg.embed_model, prompt=text)
                vec = resp["embedding"]
                if dim is None:
                    dim = len(vec)
                elif len(vec) != dim:
                    raise ValueError(f"Inconsistent embedding dimension at index {i}: expected {dim}, got {len(vec)}")
                embeddings.append(vec)
                break
            except ollama.ResponseError as e:
                logger.warning("Ollama error (attempt %d/4): %s", attempt + 1, e)
                time.sleep(2 ** attempt)
        else:
            raise RuntimeError(f"Failed to embed text at index {i} after 4 attempts")

    return embeddings
