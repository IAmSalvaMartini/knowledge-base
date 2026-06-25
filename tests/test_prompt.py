"""TEST-007: prompt.py — refusal instruction and citation markers."""
from __future__ import annotations

from retrieval.prompt import build_messages, SYSTEM_PROMPT


def test_system_prompt_contains_refusal_instruction():
    assert "I don't have that in the knowledge base" in SYSTEM_PROMPT


def test_empty_chunks_triggers_no_context_marker():
    msgs = build_messages("what is X?", [])
    user = next(m["content"] for m in msgs if m["role"] == "user")
    assert "No relevant context found" in user


def test_chunks_produce_source_markers():
    chunks = [{"text": "Cherry-pick the commit.", "metadata": {"page_path": "backport.md", "heading_path": "Backport > Intro"}}]
    msgs = build_messages("how to backport?", chunks)
    user = next(m["content"] for m in msgs if m["role"] == "user")
    assert "[source: backport.md" in user


def test_message_roles_present():
    msgs = build_messages("test?", [])
    roles = {m["role"] for m in msgs}
    assert "system" in roles
    assert "user" in roles
