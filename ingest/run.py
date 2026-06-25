from __future__ import annotations

import logging
import subprocess
from pathlib import Path

from config import load_config
from ingest import chunker, embedder, loader, sensitivity, store
from ingest.docparser import SUPPORTED_EXTENSIONS, parse_document

logger = logging.getLogger(__name__)


def _ingest_page(page, *, force: bool = False) -> bool:
    """Embed and store one page. Returns True if work was done."""
    if not sensitivity.is_ingestable(page):
        return False

    stored_hash = store.get_page_hash(page.path)
    if not force and stored_hash == page.sha256:
        logger.debug("Unchanged: %s", page.path)
        return False

    chunks = chunker.chunk_page(page)
    if not chunks:
        logger.warning("No chunks produced for: %s", page.path)
        return False

    store.delete_by_page(page.path)
    embeddings = embedder.embed_texts([c.text for c in chunks])
    store.upsert_with_hash(chunks, embeddings, page.sha256)
    logger.info("Ingested %d chunks: %s", len(chunks), page.path)
    return True


def _pull_mirror(mirror_path: Path) -> None:
    if (mirror_path / ".git").exists():
        logger.info("Pulling content mirror: %s", mirror_path)
        subprocess.run(["git", "pull", "--ff-only"], cwd=str(mirror_path), check=True)
    else:
        logger.warning("content_mirror not a git repo — skipping pull: %s", mirror_path)


def _find_deleted_pages(current_paths: set[str]) -> list[str]:
    """Return page_paths stored in Chroma that are no longer in the source."""
    col = store._get_collection()
    all_meta = col.get(include=["metadatas"])["metadatas"]
    stored_paths = {m["page_path"] for m in all_meta if "page_path" in m}
    return list(stored_paths - current_paths)


def run(force: bool = False) -> dict:
    """
    Incremental ingest from both sources:
      1. Wiki.js content_mirror (Markdown)
      2. data/uploads/ (uploaded documents)

    Returns a summary dict.
    """
    cfg = load_config()
    summary = {"ingested": 0, "skipped": 0, "deleted": 0, "errors": 0}

    # --- Source 1: Wiki.js git mirror ---
    mirror_path = cfg.content_mirror_path
    wiki_pages = []
    if mirror_path.exists():
        _pull_mirror(mirror_path)
        wiki_pages = loader.load_pages(str(mirror_path))
    else:
        logger.warning("content_mirror not found at %s — skipping wiki source", mirror_path)

    # --- Source 2: uploaded documents ---
    upload_pages = []
    uploads_path = cfg.uploads_path
    if uploads_path.exists():
        for f in uploads_path.iterdir():
            if f.suffix.lower() in SUPPORTED_EXTENSIONS:
                try:
                    upload_pages.append(parse_document(str(f)))
                except Exception as e:
                    logger.error("Failed to parse upload %s: %s", f.name, e)
                    summary["errors"] += 1

    all_pages = wiki_pages + upload_pages
    current_paths = {p.path for p in all_pages}

    # --- Delete removed pages ---
    for dead_path in _find_deleted_pages(current_paths):
        store.delete_by_page(dead_path)
        summary["deleted"] += 1
        logger.info("Deleted removed page: %s", dead_path)

    # --- Ingest changed/new pages ---
    for page in all_pages:
        try:
            did_work = _ingest_page(page, force=force)
            if did_work:
                summary["ingested"] += 1
            else:
                summary["skipped"] += 1
        except Exception as e:
            logger.error("Ingest failed for %s: %s", page.path, e)
            summary["errors"] += 1

    logger.info("Ingest complete: %s", summary)
    return summary


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    result = run()
    print(result)
