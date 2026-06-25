"""TEST-009: provider.py — abstraction and factory."""
from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest


def test_get_provider_returns_anthropic_for_default():
    os.environ["KB_LLM_PROVIDER"] = "anthropic"
    # Reset singleton
    import retrieval.provider as pmod
    pmod._provider = None

    with patch("anthropic.Anthropic"):
        from retrieval.provider import get_provider, AnthropicProvider
        p = get_provider()
        assert isinstance(p, AnthropicProvider)


def test_openai_compatible_raises_not_implemented():
    from retrieval.provider import OpenAICompatibleProvider
    with pytest.raises(NotImplementedError):
        OpenAICompatibleProvider().generate([], "model")


def test_unknown_provider_raises_value_error(monkeypatch):
    monkeypatch.setenv("KB_LLM_PROVIDER", "unknown_xyz")
    import retrieval.provider as pmod
    pmod._provider = None
    with pytest.raises(ValueError, match="Unknown KB_LLM_PROVIDER"):
        from retrieval.provider import get_provider
        get_provider()


def test_generator_does_not_import_anthropic_directly():
    """generator.py must not import the anthropic SDK directly (PAT-002)."""
    import ast
    from pathlib import Path
    src = (Path(__file__).parent.parent / "retrieval" / "generator.py").read_text()
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = [a.name for a in getattr(node, "names", [])]
            module = getattr(node, "module", "") or ""
            assert "anthropic" not in module and not any("anthropic" in n for n in names), \
                "generator.py must not import anthropic directly — use provider abstraction"
