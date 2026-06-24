"""Unit tests for ``GeminiAdapter`` chat + Google Search grounding logic.

The SDK object (``self.llm``) is replaced with a mock so the tests run offline
and assert the grounding contract: when web search is enabled the model is
invoked WITH the ``google_search`` tool, and a grounding failure degrades to an
ungrounded retry instead of breaking the turn.
"""

import asyncio
import types
from unittest.mock import AsyncMock, MagicMock

from adapters.llm.gemini_adapter import GeminiAdapter, _GOOGLE_SEARCH_TOOL
from domain.conversation.models import ChatMessage


def _adapter(web_search):
    adapter = GeminiAdapter(api_key="dummy-key", model="m", web_search=web_search)
    adapter.llm = MagicMock(name="llm")
    return adapter


def test_chat_returns_assistant_message_with_extracted_text():
    adapter = _adapter(web_search=False)
    adapter.llm.ainvoke = AsyncMock(return_value=types.SimpleNamespace(content="hola"))
    out = asyncio.run(adapter.chat([ChatMessage(role="user", content="hey")]))
    assert out.role == "assistant"
    assert out.content == "hola"


def test_invoke_uses_google_search_tool_when_web_search_enabled():
    adapter = _adapter(web_search=True)
    adapter.llm.ainvoke = AsyncMock(return_value=types.SimpleNamespace(content="x"))
    asyncio.run(adapter.chat([ChatMessage(role="user", content="noticias de hoy")]))
    assert adapter.llm.ainvoke.call_args.kwargs.get("tools") == [_GOOGLE_SEARCH_TOOL]


def test_invoke_falls_back_ungrounded_when_grounding_fails():
    adapter = _adapter(web_search=True)
    # First (grounded) call raises; the adapter must retry ungrounded.
    adapter.llm.ainvoke = AsyncMock(
        side_effect=[RuntimeError("grounding rejected"),
                     types.SimpleNamespace(content="fallback")]
    )
    out = asyncio.run(adapter.chat([ChatMessage(role="user", content="hey")]))
    assert out.content == "fallback"
    assert adapter.llm.ainvoke.call_count == 2


def test_invoke_ungrounded_when_web_search_disabled():
    adapter = _adapter(web_search=False)
    adapter.llm.ainvoke = AsyncMock(return_value=types.SimpleNamespace(content="x"))
    asyncio.run(adapter.chat([ChatMessage(role="user", content="hey")]))
    assert "tools" not in adapter.llm.ainvoke.call_args.kwargs


def test_chat_maps_roles_to_langchain_tuples():
    adapter = _adapter(web_search=False)
    adapter.llm.ainvoke = AsyncMock(return_value=types.SimpleNamespace(content="ok"))
    msgs = [
        ChatMessage(role="system", content="sys"),
        ChatMessage(role="user", content="u"),
        ChatMessage(role="assistant", content="a"),
    ]
    asyncio.run(adapter.chat(msgs))
    sent = adapter.llm.ainvoke.call_args.args[0]
    assert sent == [("system", "sys"), ("human", "u"), ("ai", "a")]
