from __future__ import annotations

import hashlib
import re
from pathlib import Path

from ingest.models import Page


_FRONT_MATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_TITLE_RE = re.compile(r"^#\s+(.+)$", re.MULTILINE)


def _parse_front_matter(raw: str) -> tuple[dict[str, str], str]:
    """Return (front_matter_dict, body_without_front_matter)."""
    m = _FRONT_MATTER_RE.match(raw)
    if not m:
        return {}, raw

    fm: dict[str, str] = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            fm[k.strip().lower()] = v.strip().strip("'\"")

    return fm, raw[m.end():]


def _extract_title(fm: dict[str, str], body: str, path: str) -> str:
    if "title" in fm:
        return fm["title"]
    m = _TITLE_RE.search(body)
    if m:
        return m.group(1).strip()
    return Path(path).stem.replace("-", " ").replace("_", " ").title()


def load_pages(mirror_path: str) -> list[Page]:
    """Walk mirror_path for *.md files and return Page records."""
    root = Path(mirror_path)
    pages: list[Page] = []

    for md_file in sorted(root.rglob("*.md")):
        raw = md_file.read_text(encoding="utf-8")
        fm, body = _parse_front_matter(raw)
        title = _extract_title(fm, body, str(md_file.relative_to(root)))
        sha = hashlib.sha256(body.encode()).hexdigest()
        pages.append(Page(
            path=str(md_file.relative_to(root)).replace("\\", "/"),
            title=title,
            body=body,
            sha256=sha,
        ))

    return pages
