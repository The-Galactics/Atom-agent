"""Shared helper to normalize LangChain message content into plain text.

Gemini 1.x/2.x return a plain ``str`` as the message content; Gemini 3.x return
a list of content blocks (``{"type": "text", "text": ..., "extras": {...}}``)
that may also include non-display blocks (reasoning / thought signatures).
``str(content)`` on the list leaks the raw block structure to clients, so every
LLM adapter must route its output through :func:`extract_text`.
"""


def extract_text(content) -> str:
    """Return only the visible text from a LangChain message ``content``."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and block.get("type") in (None, "text"):
                text = block.get("text")
                if text:
                    parts.append(text)
        # No displayable text (e.g. a tool-call response whose content is an
        # empty list, or only non-text blocks like reasoning signatures). Return
        # empty rather than leaking the raw block structure (e.g. "[]") to clients.
        return "".join(parts).strip()
    return str(content) if content else ""
