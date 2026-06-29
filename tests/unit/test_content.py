"""Unit tests for the LangChain content normalizer (``extract_text``).

Covers the Gemini 1.x/2.x plain-string path, the Gemini 3.x content-block list
path, and the regression where a tool-call response (``content == []``) used to
leak the literal ``"[]"`` to clients instead of an empty string.
"""

from adapters.llm.content import extract_text


def test_extract_text_plain_string_passthrough():
    # Gemini 1.x/2.x return a plain str — returned unchanged.
    assert extract_text("hola mundo") == "hola mundo"


def test_extract_text_joins_text_blocks():
    # Gemini 3.x return a list of content blocks; only visible text is kept.
    content = [
        {"type": "text", "text": "Hola"},
        {"type": "text", "text": " Atom"},
    ]
    assert extract_text(content) == "Hola Atom"


def test_extract_text_ignores_non_text_blocks():
    # Reasoning / thought-signature blocks are non-display and must be dropped.
    content = [
        {"type": "reasoning", "text": "pensamiento interno"},
        {"type": "text", "text": "respuesta visible"},
    ]
    assert extract_text(content) == "respuesta visible"


def test_extract_text_accepts_bare_string_blocks():
    assert extract_text(["a", "b", "c"]) == "abc"


def test_extract_text_empty_list_returns_empty_not_repr():
    # Regression: a tool-call response has content == []. It must yield "" so the
    # caller's default reply kicks in — NOT the literal "[]" leaking to clients.
    assert extract_text([]) == ""


def test_extract_text_tool_only_blocks_return_empty():
    # A list with only non-text blocks (no displayable text) -> empty string.
    content = [{"type": "reasoning", "text": "solo razonamiento"}]
    assert extract_text(content) == ""


def test_extract_text_none_returns_empty():
    assert extract_text(None) == ""
