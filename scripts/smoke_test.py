"""
Smoke test: sentence_transformers embed → ChromaDB store → query.
No LLM / API key required.
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Use a throwaway chroma dir so we don't pollute real data
import os
os.environ.setdefault("KB_CHROMA_PATH", "./data/smoke_chroma")

from ingest.models import Chunk
from ingest import embedder, store

CHUNKS = [
    Chunk("smoke/backport.md#intro-0", "smoke/backport.md", "Backporting Guide",
          "Backporting Guide > Intro",
          "To backport a fix, cherry-pick the commit onto the target release branch."),
    Chunk("smoke/backport.md#conflicts-0", "smoke/backport.md", "Backporting Guide",
          "Backporting Guide > Conflicts",
          "Resolve merge conflicts by comparing the diff against the target branch HEAD."),
    Chunk("smoke/environments.md#setup-0", "smoke/environments.md", "Environment Setup",
          "Environment Setup > Setup",
          "Set up the local environment by running the bootstrap script with the release tag."),
]

def run() -> None:
    print("-- 1. Embedding test chunks...")
    texts = [c.text for c in CHUNKS]
    vecs = embedder.embed_texts(texts)
    assert len(vecs) == len(CHUNKS), "Wrong number of embeddings"
    dim = len(vecs[0])
    assert all(len(v) == dim for v in vecs), "Inconsistent dimensions"
    print(f"   OK — {len(vecs)} vectors, dim={dim}")

    print("-- 2. Storing in ChromaDB...")
    store.upsert_with_hash(CHUNKS, vecs, sha256="smoke-test-hash")
    print("   OK")

    print("-- 3. Querying: 'how do I backport a commit?'")
    question = "how do I backport a commit?"
    q_vec = embedder.embed_texts([question])[0]
    results = store.query(q_vec, top_k=2)
    assert results, "No results returned"
    top = results[0]
    print(f"   Top hit: {top['metadata']['page_path']}")
    print(f"   Text:    {top['text'][:80]}...")
    assert "backport" in top["text"].lower(), "Top result not about backporting"
    print("   OK — correct document ranked first")

    print("-- 4. Cleanup...")
    shutil.rmtree("./data/smoke_chroma", ignore_errors=True)
    print("   OK")

    print("\nSmoke test PASSED.")

if __name__ == "__main__":
    run()
