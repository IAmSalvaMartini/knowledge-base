from __future__ import annotations

import re
from hashlib import md5

from ingest.models import Chunk, Page

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def _approx_tokens(text: str) -> int:
    return len(text) // 4


def _split_to_size(text: str, max_tokens: int, overlap: int) -> list[str]:
    """Split text into token-bounded chunks with character-level overlap."""
    max_chars = max_tokens * 4
    overlap_chars = overlap * 4

    if _approx_tokens(text) <= max_tokens:
        return [text]

    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = start + max_chars
        chunk = text[start:end]
        if chunk.strip():
            chunks.append(chunk)
        if end >= len(text):
            break
        start = end - overlap_chars

    return chunks


def chunk_page(page: Page, max_tokens: int = 800, overlap: int = 100) -> list[Chunk]:
    """Split a Page into Chunks, splitting on Markdown headings first then by size."""
    body = page.body
    chunks: list[Chunk] = []

    # Find all heading positions
    heading_matches = list(_HEADING_RE.finditer(body))

    if not heading_matches:
        # No headings — treat whole body as one section
        sections = [("", body)]
    else:
        sections: list[tuple[str, str]] = []
        for i, m in enumerate(heading_matches):
            heading_text = m.group(2).strip()
            section_start = m.end()
            section_end = heading_matches[i + 1].start() if i + 1 < len(heading_matches) else len(body)
            sections.append((heading_text, body[section_start:section_end].strip()))

        # Text before first heading
        preamble = body[:heading_matches[0].start()].strip()
        if preamble:
            sections.insert(0, ("", preamble))

    for heading, text in sections:
        if not text.strip():
            continue
        heading_path = f"{page.title} > {heading}" if heading else page.title
        sub_texts = _split_to_size(text, max_tokens, overlap)

        for idx, sub in enumerate(sub_texts):
            chunk_id = f"{page.path}#{_slug(heading or page.title)}-{idx}"
            chunks.append(Chunk(
                chunk_id=chunk_id,
                page_path=page.path,
                title=page.title,
                heading_path=heading_path,
                text=sub.strip(),
            ))

    return chunks
