from __future__ import annotations

import hashlib
import logging
from pathlib import Path

from ingest.models import Page

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".md", ".txt"}


class UnsupportedFormat(ValueError):
    pass


def _parse_pdf(path: Path) -> str:
    from pypdf import PdfReader
    reader = PdfReader(str(path))
    pages = [page.extract_text() or "" for page in reader.pages]
    text = "\n\n".join(p.strip() for p in pages if p.strip())
    if len(text) < 50:
        logger.warning("Low-yield PDF extraction: %s (%d chars)", path.name, len(text))
    return text


def _parse_docx(path: Path) -> str:
    from docx import Document
    doc = Document(str(path))
    return "\n\n".join(p.text for p in doc.paragraphs if p.text.strip())


def _parse_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def parse_document(file_path: str) -> Page:
    """Parse an uploaded file into a Page. Raises UnsupportedFormat for unknown extensions."""
    path = Path(file_path)
    ext = path.suffix.lower()

    if ext not in SUPPORTED_EXTENSIONS:
        raise UnsupportedFormat(f"Unsupported file type: {ext!r}. Allowed: {SUPPORTED_EXTENSIONS}")

    if ext == ".pdf":
        body = _parse_pdf(path)
    elif ext == ".docx":
        body = _parse_docx(path)
    else:
        body = _parse_text(path)

    sha = hashlib.sha256(body.encode()).hexdigest()
    return Page(
        path=f"upload:{path.name}",
        title=path.stem.replace("-", " ").replace("_", " ").title(),
        body=body,
        sha256=sha,
    )
