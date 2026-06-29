"""Catalog-to-Action mapping pins for the intent adapter (US-C2).

The LLM is mocked: each test feeds a tool call directly and asserts the adapter
maps it to the expected ActionType and parameters. These pins catch regressions
in the tool catalog and the adapter's mapping logic.

NOTE: because the LLM is mocked, gutting INTENT_SYSTEM_PROMPT would NOT fail
any test in this suite. Prompt-text invariants are guarded separately by the
golden assertions at the bottom of this file.
"""
import asyncio
import types
from unittest.mock import AsyncMock, MagicMock, patch

import adapters.intent.gemini_function_calling_adapter as mod
from adapters.intent.gemini_function_calling_adapter import GeminiFunctionCallingAdapter
from application.agents.prompts.intent_prompt import INTENT_SYSTEM_PROMPT
from domain.intent.models import ActionType


def _adapter(response):
    fake_bound = MagicMock()
    fake_bound.ainvoke = AsyncMock(return_value=response)
    fake_llm = MagicMock()
    fake_llm.bind_tools.return_value = fake_bound
    with patch.object(mod, "ChatGoogleGenerativeAI", return_value=fake_llm):
        return GeminiFunctionCallingAdapter(api_key="x", model="m")


def _resp(tool_calls=None, content="texto"):
    return types.SimpleNamespace(tool_calls=tool_calls or [], content=content)


# --- read_screen rule -------------------------------------------------------
# "REGLA OBLIGATORIA: cuando el usuario pida LEER, OÍR o SABER QUÉ HAY en la
# pantalla … DEBES llamar a 'read_screen' SIEMPRE"

def test_read_screen_request_routes_to_read_screen_tool():
    a = _adapter(_resp(tool_calls=[{"name": "read_screen", "args": {}}]))
    out = asyncio.run(a.recognize("léeme la pantalla"))
    assert out.action.type is ActionType.READ_SCREEN


def test_read_screen_has_no_required_parameters():
    # read_screen takes no parameters; adapter must not error on empty args.
    a = _adapter(_resp(tool_calls=[{"name": "read_screen", "args": {}}]))
    out = asyncio.run(a.recognize("qué hay en la pantalla"))
    assert out.action.type is ActionType.READ_SCREEN
    assert out.action.parameters == {}


# --- send_message / messaging priority rule ---------------------------------
# "Debes llamar UNA sola vez a send_message con app='whatsapp'"

def test_messaging_routes_to_send_message_with_whatsapp():
    a = _adapter(_resp(tool_calls=[{"name": "send_message",
                                    "args": {"app": "whatsapp", "recipient": "Juan", "body": "hola"}}]))
    out = asyncio.run(a.recognize("escríbele a Juan"))
    assert out.action.type is ActionType.SEND_MESSAGE
    assert out.action.parameters["app"] == "whatsapp"


def test_send_message_requires_confirmation():
    # send_message is flagged requires_confirmation=True in the catalog.
    a = _adapter(_resp(tool_calls=[{"name": "send_message",
                                    "args": {"recipient": "mamá", "body": "voy tarde"}}]))
    out = asyncio.run(a.recognize("dile a mamá que voy tarde"))
    assert out.action.type is ActionType.SEND_MESSAGE
    assert out.requires_confirmation is True


# --- type_text / search rule ------------------------------------------------
# "usa 'submit: true' para ejecutar la búsqueda" — adapter fills the default.

def test_type_text_defaults_submit_true():
    a = _adapter(_resp(tool_calls=[{"name": "type_text", "args": {"text": "zapatos"}}]))
    out = asyncio.run(a.recognize("busca zapatos"))
    assert out.action.type is ActionType.TYPE_TEXT
    assert out.action.parameters["submit"] is True  # default filled by adapter


def test_type_text_respects_explicit_submit_false():
    # If the model already sent submit=False the adapter must not override it.
    a = _adapter(_resp(tool_calls=[{"name": "type_text", "args": {"text": "hola", "submit": False}}]))
    out = asyncio.run(a.recognize("escribe hola"))
    assert out.action.type is ActionType.TYPE_TEXT
    assert out.action.parameters["submit"] is False


# --- tap_element rule -------------------------------------------------------
# "cuando el usuario quiera pulsar … usa 'tap_element'"

def test_tap_element_routes_correctly():
    a = _adapter(_resp(tool_calls=[{"name": "tap_element", "args": {"text": "Aceptar"}}]))
    out = asyncio.run(a.recognize("pulsa Aceptar"))
    assert out.action.type is ActionType.TAP_ELEMENT
    assert out.action.parameters["text"] == "Aceptar"


# --- navigate rule ----------------------------------------------------------

def test_navigate_back_routes_correctly():
    a = _adapter(_resp(tool_calls=[{"name": "navigate", "args": {"direction": "back"}}]))
    out = asyncio.run(a.recognize("vuelve atrás"))
    assert out.action.type is ActionType.NAVIGATE
    assert out.action.parameters["direction"] == "back"


# --- scroll rule ------------------------------------------------------------

def test_scroll_down_routes_correctly():
    a = _adapter(_resp(tool_calls=[{"name": "scroll", "args": {"direction": "down"}}]))
    out = asyncio.run(a.recognize("desplázate hacia abajo"))
    assert out.action.type is ActionType.SCROLL
    assert out.action.parameters["direction"] == "down"


# --- open_app rule ----------------------------------------------------------

def test_open_app_routes_correctly():
    a = _adapter(_resp(tool_calls=[{"name": "open_app", "args": {"app_name": "spotify"}}]))
    out = asyncio.run(a.recognize("abre spotify"))
    assert out.action.type is ActionType.OPEN_APP
    assert out.action.parameters["app_name"] == "spotify"


# --- make_call rule ---------------------------------------------------------

def test_make_call_requires_confirmation():
    a = _adapter(_resp(tool_calls=[{"name": "make_call", "args": {"target": "papá"}}]))
    out = asyncio.run(a.recognize("llama a papá"))
    assert out.action.type is ActionType.MAKE_CALL
    assert out.requires_confirmation is True


# --- golden invariants on prompt text ----------------------------------------
# The LLM is mocked above so INTENT_SYSTEM_PROMPT could be gutted without
# failing any mapping test. These assertions catch destructive prompt edits.

def test_read_screen_rule_present_in_prompt():
    assert "DEBES llamar a la herramienta 'read_screen' SIEMPRE" in INTENT_SYSTEM_PROMPT


def test_messaging_priority_rule_present_in_prompt():
    assert "REGLA DE PRIORIDAD DE MENSAJERÍA" in INTENT_SYSTEM_PROMPT


def test_ecommerce_fake_search_bar_rule_present_in_prompt():
    assert "REGLA DE BARRAS DE BÚSQUEDA FALSAS (E-commerce)" in INTENT_SYSTEM_PROMPT
