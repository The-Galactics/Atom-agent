"""Unit tests for ``GeminiFunctionCallingAdapter`` with the Gemini client mocked.

The ``ChatGoogleGenerativeAI`` SDK object is fully replaced so these tests run
offline (no API key, no network) while still exercising the adapter's mapping
logic: tool-call -> Action, sensitive-action confirmation, conversational
fallback, unknown-tool degradation, provider-error wrapping and date injection.
"""

import asyncio
import types
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import adapters.intent.gemini_function_calling_adapter as mod
from adapters.intent.gemini_function_calling_adapter import GeminiFunctionCallingAdapter
from domain.errors import ProviderError
from domain.intent.models import ActionType


def _make_adapter(response=None, raise_exc=None):
    """Construct the adapter with ChatGoogleGenerativeAI mocked out.

    Returns (adapter, fake_bound_llm) so tests can inspect ``ainvoke`` calls.
    """
    fake_bound = MagicMock(name="bound_llm")
    if raise_exc is not None:
        fake_bound.ainvoke = AsyncMock(side_effect=raise_exc)
    else:
        fake_bound.ainvoke = AsyncMock(return_value=response)
    fake_llm = MagicMock(name="llm")
    fake_llm.bind_tools.return_value = fake_bound
    with patch.object(mod, "ChatGoogleGenerativeAI", return_value=fake_llm):
        adapter = GeminiFunctionCallingAdapter(
            api_key="unused", model="m", timezone="America/Bogota"
        )
    return adapter, fake_bound


def _resp(tool_calls=None, content="texto"):
    return types.SimpleNamespace(tool_calls=tool_calls or [], content=content)


def test_recognize_maps_tool_call_to_action():
    resp = _resp(tool_calls=[{"name": "open_app", "args": {"app_name": "spotify"}}], content=[])
    adapter, _ = _make_adapter(response=resp)
    result = asyncio.run(adapter.recognize("abre spotify"))
    assert result.action.type is ActionType.OPEN_APP
    assert result.action.parameters == {"app_name": "spotify"}
    assert result.confidence == 1.0
    assert result.requires_confirmation is False


def test_recognize_marks_sensitive_action_for_confirmation():
    resp = _resp(tool_calls=[{"name": "make_call", "args": {"target": "mamá"}}], content=[])
    adapter, _ = _make_adapter(response=resp)
    result = asyncio.run(adapter.recognize("llama a mamá"))
    assert result.action.type is ActionType.MAKE_CALL
    assert result.requires_confirmation is True


def test_recognize_conversational_when_no_tool_call():
    resp = _resp(tool_calls=[], content="¡Hola!")
    adapter, _ = _make_adapter(response=resp)
    result = asyncio.run(adapter.recognize("hola"))
    assert result.action.type is ActionType.NONE
    assert result.reply == "¡Hola!"
    assert result.confidence == 0.0


def test_recognize_unknown_tool_degrades_to_conversation():
    resp = _resp(tool_calls=[{"name": "teleport", "args": {}}], content="no puedo")
    adapter, _ = _make_adapter(response=resp)
    result = asyncio.run(adapter.recognize("teletranspórtame"))
    assert result.action.type is ActionType.NONE
    assert result.confidence == 0.0


def test_recognize_wraps_provider_errors():
    adapter, _ = _make_adapter(raise_exc=RuntimeError("boom"))
    with pytest.raises(ProviderError):
        asyncio.run(adapter.recognize("hola"))


def test_recognize_injects_current_date_into_system_prompt():
    adapter, fake_bound = _make_adapter(response=_resp(tool_calls=[], content="ok"))
    asyncio.run(adapter.recognize("¿qué día es hoy?"))
    messages = fake_bound.ainvoke.call_args.args[0]
    role, text = messages[0]
    assert role == "system"
    assert "Fecha y hora actuales" in text
