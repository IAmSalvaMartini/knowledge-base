"""TEST-003: sensitivity.py"""
from __future__ import annotations

from ingest.models import Page
from ingest.sensitivity import is_ingestable


def _page(body: str) -> Page:
    return Page(path="x.md", title="X", body=body, sha256="abc")


def test_normal_page_passes():
    assert is_ingestable(_page("# Guide\nSome content.")) is True


def test_restricted_front_matter_rejected():
    body = "---\nsensitivity: restricted\ntitle: Secret\n---\nTop secret."
    assert is_ingestable(_page(body)) is False


def test_restricted_case_insensitive():
    body = "---\nSensitivity: RESTRICTED\n---\nContent."
    assert is_ingestable(_page(body)) is False


def test_restricted_in_body_not_blocked():
    # 'restricted' keyword in body text (not front matter) should NOT block
    body = "# Policy\nAccess is restricted to admins."
    assert is_ingestable(_page(body)) is True
