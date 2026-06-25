"""TEST-010: docparser.py — file parsing and UnsupportedFormat."""
from __future__ import annotations

from pathlib import Path

import pytest

from ingest.docparser import parse_document, UnsupportedFormat


def test_parse_markdown(tmp_path):
    f = tmp_path / "guide.md"
    f.write_text("# Guide\nSome content.", encoding="utf-8")
    page = parse_document(str(f))
    assert page.path == "upload:guide.md"
    assert "Guide" in page.body


def test_parse_txt(tmp_path):
    f = tmp_path / "notes.txt"
    f.write_text("Important notes here.", encoding="utf-8")
    page = parse_document(str(f))
    assert page.path == "upload:notes.txt"
    assert "Important notes" in page.body


def test_unsupported_extension_raises(tmp_path):
    f = tmp_path / "data.xlsx"
    f.write_bytes(b"fakecontent")
    with pytest.raises(UnsupportedFormat):
        parse_document(str(f))


def test_sha256_is_hex_string(tmp_path):
    f = tmp_path / "a.txt"
    f.write_text("hello", encoding="utf-8")
    page = parse_document(str(f))
    assert len(page.sha256) == 64
    assert all(c in "0123456789abcdef" for c in page.sha256)


def test_title_derived_from_filename(tmp_path):
    f = tmp_path / "my-doc.txt"
    f.write_text("content", encoding="utf-8")
    page = parse_document(str(f))
    assert page.title == "My Doc"
