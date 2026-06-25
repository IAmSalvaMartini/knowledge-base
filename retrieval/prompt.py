from __future__ import annotations

SYSTEM_PROMPT = """\
You are a knowledge base assistant for an engineering organization.
Answer questions using ONLY the context passages provided below.
Rules:
- Cite every claim with [source: <page_path>] inline.
- If the context does not contain enough information to answer, reply exactly:
  "I don't have that in the knowledge base."
- Do not invent facts. Do not use knowledge outside the provided context.
- Be concise. Use Markdown formatting for readability.
"""


def build_messages(question: str, chunks: list[dict]) -> list[dict]:
    """Build a provider-neutral messages payload for RAG generation."""
    if not chunks:
        context_block = "(No relevant context found.)"
    else:
        parts = []
        for c in chunks:
            meta = c.get("metadata", {})
            source = meta.get("page_path", "unknown")
            heading = meta.get("heading_path", "")
            label = f"{source}" + (f" — {heading}" if heading else "")
            parts.append(f"[source: {label}]\n{c['text']}")
        context_block = "\n\n---\n\n".join(parts)

    user_content = f"Context:\n\n{context_block}\n\nQuestion: {question}"

    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]
