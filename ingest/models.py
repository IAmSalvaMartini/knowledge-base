from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Page:
    path: str       # content_mirror-relative path OR "upload:<filename>"
    title: str
    body: str
    sha256: str     # hash of body — used for incremental ingest comparison


@dataclass
class Chunk:
    chunk_id: str       # "<page_path>#<heading_slug>-<index>"
    page_path: str
    title: str          # page title
    heading_path: str   # e.g. "Setup > Installation"
    text: str
