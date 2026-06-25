from __future__ import annotations

import logging
from pathlib import Path

from flask import Blueprint, flash, redirect, render_template, request, url_for

from auth.oidc import login_required
from config import load_config
from ingest.docparser import SUPPORTED_EXTENSIONS, UnsupportedFormat, parse_document
from ingest.run import _ingest_page

logger = logging.getLogger(__name__)

bp = Blueprint("upload", __name__, url_prefix="/upload", template_folder="templates")

# Allowed MIME types per extension (SEC-006)
_ALLOWED_MIME: dict[str, set[str]] = {
    ".pdf": {"application/pdf"},
    ".docx": {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/octet-stream",
    },
    ".md": {"text/markdown", "text/plain", "application/octet-stream"},
    ".txt": {"text/plain", "application/octet-stream"},
}


@bp.get("/")
@login_required
def upload_form():
    cfg = load_config()
    return render_template(
        "upload.html",
        supported=sorted(SUPPORTED_EXTENSIONS),
        max_upload_mb=cfg.max_upload_mb,
    )


@bp.post("/")
@login_required
def upload_file():
    cfg = load_config()

    if "file" not in request.files or not request.files["file"].filename:
        flash("No file selected.", "error")
        return redirect(url_for("upload.upload_form"))

    f = request.files["file"]
    filename = Path(f.filename).name  # strip any path components
    ext = Path(filename).suffix.lower()

    # Extension allowlist (SEC-006)
    if ext not in SUPPORTED_EXTENSIONS:
        flash(f"Unsupported type: {ext}. Allowed: {', '.join(sorted(SUPPORTED_EXTENSIONS))}", "error")
        return redirect(url_for("upload.upload_form"))

    # Content-type validation (SEC-006)
    content_type = (f.content_type or "").split(";")[0].strip()
    if content_type and content_type not in _ALLOWED_MIME.get(ext, set()):
        logger.warning("Suspicious content-type %r for %s", content_type, filename)
        flash("Content type does not match file extension.", "error")
        return redirect(url_for("upload.upload_form"))

    # Size check (SEC-006)
    f.seek(0, 2)
    size_mb = f.tell() / (1024 * 1024)
    f.seek(0)
    if size_mb > cfg.max_upload_mb:
        flash(f"File too large ({size_mb:.1f} MB). Max: {cfg.max_upload_mb} MB.", "error")
        return redirect(url_for("upload.upload_form"))

    # Save
    cfg.uploads_path.mkdir(parents=True, exist_ok=True)
    save_path = cfg.uploads_path / filename
    f.save(str(save_path))
    logger.info("Saved upload: %s (%.2f MB)", filename, size_mb)

    # Ingest
    try:
        page = parse_document(str(save_path))
        _ingest_page(page, force=True)
        flash(f'"{filename}" ingested successfully.', "success")
    except UnsupportedFormat as e:
        flash(str(e), "error")
    except Exception as e:
        logger.exception("Ingest failed for %s", filename)
        flash(f"Ingest failed: {e}", "error")

    return redirect(url_for("upload.upload_form"))
