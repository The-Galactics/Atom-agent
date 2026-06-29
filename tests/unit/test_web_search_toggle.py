"""Task 6: web-search default OFF + per-call adapter override.

Tests the two behaviour contracts:
  1. config default is False (web_search_enabled).
  2. adapter honours the per-call web_search override regardless of the
     construction-time default.
"""

import asyncio
from unittest.mock import AsyncMock

from adapters.llm.gemini_adapter import GeminiAdapter
from domain.conversation.models import ChatMessage
from infrastructure.config import get_settings


def _adapter(web_search):
    a = GeminiAdapter(api_key="k", web_search=web_search)
    a.llm = AsyncMock()
    a.llm.ainvoke.return_value = type("R", (), {"content": "ok"})()
    return a


def test_default_off_attaches_no_tool():
    a = _adapter(web_search=False)
    asyncio.run(a.chat([ChatMessage(role="user", content="hi")]))
    _, kwargs = a.llm.ainvoke.call_args
    assert "tools" not in kwargs or not kwargs["tools"]


def test_per_call_override_true_attaches_tool():
    a = _adapter(web_search=False)
    asyncio.run(a.chat([ChatMessage(role="user", content="hi")], web_search=True))
    _, kwargs = a.llm.ainvoke.call_args
    assert kwargs.get("tools")


def test_per_call_override_false_forces_off():
    a = _adapter(web_search=True)
    asyncio.run(a.chat([ChatMessage(role="user", content="hi")], web_search=False))
    _, kwargs = a.llm.ainvoke.call_args
    assert "tools" not in kwargs or not kwargs["tools"]


def test_config_default_is_off(monkeypatch):
    monkeypatch.delenv("WEB_SEARCH_ENABLED", raising=False)
    get_settings.cache_clear()
    assert get_settings().web_search_enabled is False
    get_settings.cache_clear()   # leave no cached Settings for other tests
