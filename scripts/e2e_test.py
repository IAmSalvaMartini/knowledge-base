"""
End-to-end pipeline test — no API key required.
Real: sentence_transformers embed, ChromaDB store/query, prompt build.
Mocked: AnthropicProvider.generate returns a canned cited answer.
"""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# --- Config ------------------------------------------------------------------
MIRROR = Path("./data/e2e_mirror")
os.environ["KB_EMBED_BACKEND"] = "sentence_transformers"
os.environ["KB_EMBED_MODEL"] = "all-MiniLM-L6-v2"
os.environ["KB_CHROMA_PATH"] = "./data/e2e_chroma"
os.environ["KB_UPLOADS_PATH"] = "./data/uploads"
os.environ["KB_CONTENT_MIRROR_PATH"] = str(MIRROR)
os.environ["KB_TOP_K"] = "3"
os.environ.setdefault("KB_FLASK_SECRET_KEY", "e2e")
os.environ.setdefault("ANTHROPIC_API_KEY", "fake-key-not-used")

# Reset cached singletons
import ingest.store as _s, ingest.embedder as _e
_s._collection = None
_e._backend = None

# --- Seed content mirror -----------------------------------------------------
print("-- 1. Seeding content mirror...")
MIRROR.mkdir(parents=True, exist_ok=True)
(MIRROR / "backporting.md").write_text("""\
---
title: Backporting Guide
---
## Overview
To backport a fix, cherry-pick the commit SHA onto the target release branch
using `git cherry-pick <sha>`. Resolve any conflicts against the target HEAD.

## Conflict Resolution
Compare the diff with `git diff <base>..HEAD` and manually reconcile
changes that conflict with the target branch structure.
""", encoding="utf-8")

(MIRROR / "environments.md").write_text("""\
---
title: Environment Setup
---
## Local Setup
Run `bootstrap.sh <release-tag>` to initialise the local environment.
Set `APP_HOME` to your application installation directory before running.

## Common Issues
If bootstrap fails with `ERR_MODULE_NOT_FOUND`, check that Node.js >= 18 is on PATH.
""", encoding="utf-8")

(MIRROR / "people.md").write_text("""\
---
title: People and Ownership
---
## Ownership
The release pipeline is owned by the Release Engineering team.
Contact @release-eng on the internal chat for urgent requests.
""", encoding="utf-8")

# --- Run ingest --------------------------------------------------------------
print("-- 2. Running ingest pipeline...")
from ingest.run import run
with patch("ingest.run._pull_mirror"):  # skip git pull, mirror already seeded
    summary = run(force=True)
print(f"   {summary}")

# --- Ask a question (mocked LLM) ---------------------------------------------
print("-- 3. Asking: 'how do I backport a fix to a release branch?'")
QUESTION = "how do I backport a fix to a release branch?"

from retrieval import retriever, prompt

chunks = retriever.retrieve(QUESTION, top_k=3)
print(f"   Retrieved {len(chunks)} chunks:")
for c in chunks:
    print(f"     [{c['metadata']['page_path']}] {c['text'][:60]}...")

messages = prompt.build_messages(QUESTION, chunks)

# Fake LLM response that cites the retrieved source
FAKE_RESPONSE = (
    "To backport a fix, cherry-pick the commit onto the target release branch "
    "using `git cherry-pick <sha>` [source: backporting.md]. "
    "Resolve any conflicts by comparing the diff against the target HEAD "
    "[source: backporting.md -- Conflict Resolution]."
)

from retrieval.generator import Answer, _extract_citations

answer = Answer(
    text=FAKE_RESPONSE,
    citations=_extract_citations(FAKE_RESPONSE),
)

print(f"\n   Answer:\n   {answer.text}")
print(f"\n   Citations: {answer.citations}")

# --- Assertions --------------------------------------------------------------
assert len(chunks) > 0, "No chunks retrieved"
assert chunks[0]["metadata"]["page_path"] == "backporting.md", \
    f"Wrong top chunk: {chunks[0]['metadata']['page_path']}"
assert len(answer.citations) >= 1, "No citations extracted"
print("\nE2E test PASSED.")

# --- Cleanup -----------------------------------------------------------------
shutil.rmtree("./data/e2e_chroma", ignore_errors=True)
shutil.rmtree(str(MIRROR), ignore_errors=True)
