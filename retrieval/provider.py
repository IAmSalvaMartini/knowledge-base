from __future__ import annotations

import logging
from abc import ABC, abstractmethod

from config import load_config

logger = logging.getLogger(__name__)


class LLMProvider(ABC):
    @abstractmethod
    def generate(self, messages: list[dict], model: str) -> str:
        ...


class AnthropicProvider(LLMProvider):
    def __init__(self) -> None:
        import anthropic
        cfg = load_config()
        self._client = anthropic.Anthropic(api_key=cfg.anthropic_api_key)

    def generate(self, messages: list[dict], model: str) -> str:
        system = next((m["content"] for m in messages if m["role"] == "system"), None)
        user_messages = [m for m in messages if m["role"] != "system"]

        kwargs: dict = dict(model=model, max_tokens=2048, messages=user_messages)
        if system:
            kwargs["system"] = system

        response = self._client.messages.create(**kwargs)
        return response.content[0].text


class OpenAICompatibleProvider(LLMProvider):
    def generate(self, messages: list[dict], model: str) -> str:
        raise NotImplementedError(
            "OpenAICompatibleProvider not implemented. "
            "Set KB_LLM_PROVIDER=anthropic or implement this class."
        )


_provider: LLMProvider | None = None


def get_provider() -> LLMProvider:
    global _provider
    if _provider is None:
        cfg = load_config()
        if cfg.llm_provider == "anthropic":
            _provider = AnthropicProvider()
        elif cfg.llm_provider == "openai_compatible":
            _provider = OpenAICompatibleProvider()
        else:
            raise ValueError(f"Unknown KB_LLM_PROVIDER: {cfg.llm_provider!r}")
    return _provider
