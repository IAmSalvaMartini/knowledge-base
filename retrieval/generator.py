from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

from config import load_config
from retrieval import prompt, retriever
from retrieval.provider import get_provider

logger = logging.getLogger(__name__)

_CITATION_RE = re.compile(r"\[source:\s*([^\]]+)\]")
_NO_ANSWER = "I don't have that in the knowledge base."
_LOW_CONFIDENCE_MARKER = _NO_ANSWER


@dataclass
class Answer:
    text: str
    citations: list[str] = field(default_factory=list)


def _extract_citations(text: str) -> list[str]:
    return list(dict.fromkeys(_CITATION_RE.findall(text)))


def answer(question: str) -> Answer:
    """RAG answer with automatic escalation to a stronger model when needed."""
    cfg = load_config()
    provider = get_provider()

    chunks = retriever.retrieve(question)
    messages = prompt.build_messages(question, chunks)

    # First attempt with the default (cheaper) model
    text = provider.generate(messages, cfg.answer_model)

    # Escalate if: no context retrieved, or model admitted it doesn't know
    should_escalate = (
        not chunks
        or _LOW_CONFIDENCE_MARKER in text
        or len(chunks) < cfg.top_k // 2
    )

    if should_escalate and cfg.answer_model != cfg.escalation_model:
        logger.info("Escalating to %s", cfg.escalation_model)
        text = provider.generate(messages, cfg.escalation_model)

    citations = _extract_citations(text)
    return Answer(text=text, citations=citations)
