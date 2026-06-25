"""TEST-001: loader.py"""
from __future__ import annotations

from pathlib import Path

import pytest

from ingest.loader import load_pages


@pytest.fixture()
def mirror(tmp_path):
    (tmp_path / "guide.md").write_text(
        "---\ntitle: Backport Guide\n---\n# Backport Guide\nCherry-pick the commit.",
        encoding="utf-8",
    )
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "env.md").write_text("# Environments\nRun bootstrap.sh.", encoding="utf-8")
    return tmp_path


def test_returns_correct_count(mirror):
    pages = load_pages(str(mirror))
    assert len(pages) == 2


def test_title_from_front_matter(mirror):
    pages = {p.path: p for p in load_pages(str(mirror))}
    assert pages["guide.md"].title == "Backport Guide"


def test_title_fallback_to_h1(mirror):
    pages = {p.path: p for p in load_pages(str(mirror))}
    assert pages["sub/env.md"].title == "Environments"


def test_sha256_stable(mirror):
    pages1 = load_pages(str(mirror))
    pages2 = load_pages(str(mirror))
    hashes1 = {p.path: p.sha256 for p in pages1}
    hashes2 = {p.path: p.sha256 for p in pages2}
    assert hashes1 == hashes2


def test_sha256_changes_on_edit(mirror):
    p = mirror / "guide.md"
    pages_before = {pg.path: pg for pg in load_pages(str(mirror))}
    p.write_text(p.read_text(encoding="utf-8") + "\nExtra line.", encoding="utf-8")
    pages_after = {pg.path: pg for pg in load_pages(str(mirror))}
    assert pages_before["guide.md"].sha256 != pages_after["guide.md"].sha256
