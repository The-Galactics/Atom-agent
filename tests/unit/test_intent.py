import asyncio
from unittest.mock import patch

from adapters.intent.gemini_function_calling_adapter import _SYSTEM_PROMPT
from application.dtos import ExecuteCommandInputDTO
from application.use_cases.execute_command import ExecuteCommandUseCase
from domain.intent.catalog import ACTION_CATALOG, openai_tools, spec_for_tool
from domain.intent.models import Action, ActionType, IntentResult
from ports.intent_port import IntentRecognizerPort


class FakeIntentRecognizer(IntentRecognizerPort):
    """Records the last call and returns a canned IntentResult."""

    def __init__(self, result: IntentResult):
        self._result = result
        self.last_text = None
        self.last_session = None
        self.last_screen = None

    async def recognize(
        self, text: str, session_id: str = "default", screen=None
    ) -> IntentResult:
        self.last_text = text
        self.last_session = session_id
        self.last_screen = screen
        return self._result


# --- domain / catalog -------------------------------------------------------

def test_action_type_from_string_is_case_insensitive():
    assert ActionType.from_string("open_app") is ActionType.OPEN_APP
    assert ActionType.from_string("MAKE_CALL") is ActionType.MAKE_CALL


def test_action_type_from_string_unknown_falls_back_to_none():
    assert ActionType.from_string("teleport") is ActionType.NONE


def test_every_action_spec_has_a_distinct_tool_name():
    names = [spec.tool_name for spec in ACTION_CATALOG]
    assert len(names) == len(set(names))


def test_openai_tools_shape_matches_bind_tools_contract():
    tools = openai_tools()
    assert len(tools) == len(ACTION_CATALOG)
    for tool in tools:
        assert tool["type"] == "function"
        fn = tool["function"]
        assert fn["name"] and fn["description"]
        assert fn["parameters"]["type"] == "object"


def test_spec_for_tool_resolves_and_marks_sensitive_actions():
    assert spec_for_tool("open_app").requires_confirmation is False
    assert spec_for_tool("make_call").requires_confirmation is True
    assert spec_for_tool("nonexistent") is None


def test_accessibility_actions_are_registered():
    for tool_name, action_type in (
        ("navigate", ActionType.NAVIGATE),
        ("scroll", ActionType.SCROLL),
        ("read_screen", ActionType.READ_SCREEN),
        ("tap_element", ActionType.TAP_ELEMENT),
    ):
        spec = spec_for_tool(tool_name)
        assert spec is not None, tool_name
        assert spec.type is action_type


def test_only_tap_element_confirms_among_accessibility_actions():
    assert spec_for_tool("navigate").requires_confirmation is False
    assert spec_for_tool("scroll").requires_confirmation is False
    assert spec_for_tool("read_screen").requires_confirmation is False
    assert spec_for_tool("tap_element").requires_confirmation is True


def test_type_text_action_is_registered():
    spec = spec_for_tool("type_text")
    assert spec is not None
    # Wire string the Android client maps via ActionType.fromWire must be exact.
    assert spec.type is ActionType.TYPE_TEXT
    assert spec.type.value == "TYPE_TEXT"
    # Typing a query is not destructive -> no on-device confirmation.
    assert spec.requires_confirmation is False


def test_alarm_and_timer_param_descriptions_steer_parseable_values():
    # B4 defense-in-depth: at temperature 0 the catalog param descriptions steer
    # the model to emit values the Android side can parse with parseInt/parseDouble,
    # so non-numeric input ("mediodía", "cinco minutos") rarely reaches the device.
    alarm = spec_for_tool("set_alarm")
    time_param = next(p for p in alarm.parameters if p.name == "time")
    assert "HH:MM" in time_param.description

    timer = spec_for_tool("set_timer")
    duration_param = next(p for p in timer.parameters if p.name == "duration_seconds")
    assert "SEGUNDOS" in duration_param.description


def test_type_text_tool_schema_exposes_text_and_optional_submit():
    fn = {t["function"]["name"]: t["function"] for t in openai_tools()}["type_text"]
    props = fn["parameters"]["properties"]
    assert props["text"]["type"] == "string"
    assert props["submit"]["type"] == "boolean"
    # text required, submit optional (defaulted on the backend).
    assert fn["parameters"]["required"] == ["text"]


def test_accessibility_tool_schemas_expose_their_params():
    tools = {t["function"]["name"]: t["function"] for t in openai_tools()}
    # direction enums are surfaced to the LLM
    assert set(tools["navigate"]["parameters"]["properties"]["direction"]["enum"]) == {
        "back", "home", "recents", "quick_settings"
    }
    assert set(tools["scroll"]["parameters"]["properties"]["direction"]["enum"]) == {
        "up", "down", "left", "right"
    }
    # read_screen takes no parameters; tap_element requires its text slot
    assert tools["read_screen"]["parameters"]["properties"] == {}
    assert tools["tap_element"]["parameters"]["required"] == ["text"]


# --- use case ---------------------------------------------------------------

def test_execute_command_maps_recognized_action():
    recognizer = FakeIntentRecognizer(
        IntentResult(
            action=Action(type=ActionType.OPEN_APP, parameters={"app_name": "whatsapp"}),
            reply="Abriendo WhatsApp.",
            confidence=1.0,
        )
    )
    use_case = ExecuteCommandUseCase(intent_recognizer=recognizer)

    output = asyncio.run(use_case.execute(ExecuteCommandInputDTO(text="abre whatsapp", user_id="u1")))

    assert output.success is True
    assert output.action_type == "OPEN_APP"
    assert output.parameters == {"app_name": "whatsapp"}
    assert output.reply_text == "Abriendo WhatsApp."
    assert recognizer.last_session == "u1"


def test_execute_command_sensitive_action_requires_confirmation():
    recognizer = FakeIntentRecognizer(
        IntentResult(
            action=Action(type=ActionType.MAKE_CALL, parameters={"target": "mamá"}),
            reply="",
            confidence=1.0,
            requires_confirmation=True,
        )
    )
    use_case = ExecuteCommandUseCase(intent_recognizer=recognizer)

    output = asyncio.run(use_case.execute(ExecuteCommandInputDTO(text="llama a mamá")))

    assert output.action_type == "MAKE_CALL"
    assert output.requires_confirmation is True
    # Bare tool call without text gets a default spoken confirmation.
    assert output.reply_text == "De acuerdo."


def test_execute_command_forwards_screen_to_recognizer():
    recognizer = FakeIntentRecognizer(
        IntentResult(action=Action(type=ActionType.NONE), reply="ok", confidence=0.0)
    )
    use_case = ExecuteCommandUseCase(intent_recognizer=recognizer)
    screen = [{"index": 0, "role": "Button", "text": "Aceptar", "clickable": True}]

    asyncio.run(
        use_case.execute(
            ExecuteCommandInputDTO(text="pulsa aceptar", user_id="u1", screen_elements=screen)
        )
    )

    assert recognizer.last_screen == screen


# --- gemini adapter (LLM mocked, no network/key) ----------------------------


class _StubResponse:
    """Mimics a langchain AIMessage enough for the adapter."""

    def __init__(self, content="hola", tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls or []


class _CapturingLLM:
    """Stand-in for the bound model: records messages, returns a canned response."""

    def __init__(self, response):
        self._response = response
        self.captured_messages = None

    async def ainvoke(self, messages):
        self.captured_messages = messages
        return self._response


def _make_adapter(response):
    """Build a GeminiFunctionCallingAdapter with its LLM fully patched out."""
    captured = _CapturingLLM(response)

    class _FakeLLM:
        def __init__(self, *a, **k):
            pass

        def bind_tools(self, tools):
            return captured

    # Patch the LLM client in the adapter module so no key/network is needed.
    import adapters.intent.gemini_function_calling_adapter as mod

    with patch.object(mod, "ChatGoogleGenerativeAI", _FakeLLM):
        adapter = mod.GeminiFunctionCallingAdapter(api_key="dummy")
    return adapter, captured


def test_adapter_renders_screen_into_messages():
    adapter, captured = _make_adapter(_StubResponse(content="vale"))
    screen = [
        {"index": 0, "role": "Button", "text": "Aceptar", "clickable": True},
        {"index": 1, "role": "EditText", "text": "Buscar", "editable": True, "focusable": True},
    ]

    asyncio.run(adapter.recognize("pulsa aceptar", screen=screen))

    rendered = "\n".join(str(m) for m in captured.captured_messages)
    assert "Elementos visibles en la pantalla actual" in rendered
    assert '[0] Button "Aceptar" (clickable)' in rendered
    assert '[1] EditText "Buscar" (focusable,editable)' in rendered


def test_adapter_resolves_read_screen_tool_call():
    # A read_screen tool call must map to READ_SCREEN at full confidence even
    # when screen elements are present (regression: model used to answer
    # conversationally from the injected context instead of calling the tool).
    response = _StubResponse(
        content="",
        tool_calls=[{"name": "read_screen", "args": {}, "id": "1"}],
    )
    adapter, _ = _make_adapter(response)
    screen = [{"index": 0, "role": "TextView", "text": "Configuración"}]

    result = asyncio.run(adapter.recognize("lee la pantalla", screen=screen))

    assert result.action.type is ActionType.READ_SCREEN
    assert result.confidence == 1.0
    assert result.requires_confirmation is False


def test_adapter_resolves_type_text_to_uppercase_wire_string():
    # Integration-critical: a type_text tool call must resolve to the exact
    # uppercase wire string "TYPE_TEXT" the Android client expects.
    response = _StubResponse(
        content="",
        tool_calls=[
            {"name": "type_text", "args": {"text": "Rubius cartas Pokémon", "submit": True}, "id": "1"}
        ],
    )
    adapter, _ = _make_adapter(response)

    result = asyncio.run(adapter.recognize("busca un video del Rubius sobre cartas Pokémon"))

    assert result.action.type is ActionType.TYPE_TEXT
    assert result.action.type.value == "TYPE_TEXT"
    assert result.action.parameters == {"text": "Rubius cartas Pokémon", "submit": True}
    assert result.confidence == 1.0
    assert result.requires_confirmation is False


def test_adapter_type_text_defaults_submit_true_when_omitted():
    # The model may omit the optional 'submit' slot; the adapter fills the
    # contract default so the wire params always carry submit.
    response = _StubResponse(
        content="",
        tool_calls=[{"name": "type_text", "args": {"text": "gatos"}, "id": "1"}],
    )
    adapter, _ = _make_adapter(response)

    result = asyncio.run(adapter.recognize("busca gatos"))

    assert result.action.parameters == {"text": "gatos", "submit": True}


def test_execute_command_youtube_search_screen_yields_type_text():
    # Simulated YouTube search screen: an editable, focused search box. The
    # resolved action must be TYPE_TEXT carrying the query (end-to-end via the
    # use case, with the LLM tool call mocked deterministically).
    response = _StubResponse(
        content="",
        tool_calls=[
            {"name": "type_text", "args": {"text": "Rubius cartas Pokémon", "submit": True}, "id": "1"}
        ],
    )
    adapter, _ = _make_adapter(response)
    use_case = ExecuteCommandUseCase(intent_recognizer=adapter)
    youtube_search_screen = [
        {"index": 0, "role": "EditText", "text": "", "editable": True, "focusable": True},
        {"index": 1, "role": "Button", "text": "Buscar", "clickable": True},
    ]

    output = asyncio.run(
        use_case.execute(
            ExecuteCommandInputDTO(
                text="busca un video del Rubius sobre cartas Pokémon",
                user_id="u-yt",
                screen_elements=youtube_search_screen,
            )
        )
    )

    assert output.action_type == "TYPE_TEXT"
    assert output.parameters == {"text": "Rubius cartas Pokémon", "submit": True}


def test_system_prompt_instructs_type_text_for_input_fields():
    import adapters.intent.gemini_function_calling_adapter as mod

    prompt = mod._SYSTEM_PROMPT.lower()
    assert "type_text" in prompt
    # Mentions submit-to-run-the-search and the editable/search field intent.
    assert "submit" in prompt
    assert "búsqueda" in prompt or "editable" in prompt


def test_system_prompt_contains_fake_search_bar_rule():
    # The "Interactive UI Illusion Rule" must be present so the model taps a
    # non-editable search container before trying to type into it.
    assert "BARRAS DE BÚSQUEDA FALSAS" in _SYSTEM_PROMPT
    assert "tap_element" in _SYSTEM_PROMPT
    assert "turno inmediato siguiente" in _SYSTEM_PROMPT


def test_system_prompt_prioritizes_instant_messaging_over_sms():
    import adapters.intent.gemini_function_calling_adapter as mod
    prompt = mod._SYSTEM_PROMPT
    assert "REGLA DE PRIORIDAD DE MENSAJERÍA" in prompt
    assert "PROHIBIDO" in prompt
    assert "send_message" in prompt
    assert "app='whatsapp'" in prompt
    assert "NUNCA ejecutes además un `OPEN_APP`" in prompt


def test_system_prompt_mandates_read_screen_tool():
    # The prompt must firmly instruct the lite model to call read_screen for
    # "read the screen" style requests rather than reply from context.
    import adapters.intent.gemini_function_calling_adapter as mod

    prompt = mod._SYSTEM_PROMPT.lower()
    assert "read_screen" in prompt
    assert "lee la pantalla" in prompt
    assert "qué hay en la pantalla" in prompt


def test_adapter_without_screen_sends_only_system_and_human():
    adapter, captured = _make_adapter(_StubResponse(content="hola"))

    asyncio.run(adapter.recognize("hola"))

    # system + human, no screen message appended.
    assert len(captured.captured_messages) == 2
    rendered = "\n".join(str(m) for m in captured.captured_messages)
    assert "Elementos visibles en la pantalla actual" not in rendered


def test_adapter_renders_history_into_messages():
    # The accumulated ReAct trace must reach the model as a context message so
    # it can decide the next step.
    adapter, captured = _make_adapter(_StubResponse(content="vale"))
    history = [
        "Step 1: OPEN_APP {'app_name': 'youtube'}",
        "Step 2: TAP_ELEMENT {'text': 'Buscar'}",
    ]

    asyncio.run(adapter.recognize("abre youtube y busca", history=history))

    rendered = "\n".join(str(m) for m in captured.captured_messages)
    assert "Acciones ya ejecutadas en esta tarea (ReAct)" in rendered
    assert "Step 1: OPEN_APP {'app_name': 'youtube'}" in rendered
    assert "Step 2: TAP_ELEMENT {'text': 'Buscar'}" in rendered


def test_adapter_renders_both_history_and_screen():
    adapter, captured = _make_adapter(_StubResponse(content="vale"))
    history = ["Step 1: OPEN_APP {'app_name': 'youtube'}"]
    screen = [{"index": 0, "role": "Button", "text": "Buscar", "clickable": True}]

    asyncio.run(adapter.recognize("busca", screen=screen, history=history))

    rendered = "\n".join(str(m) for m in captured.captured_messages)
    assert "Acciones ya ejecutadas en esta tarea (ReAct)" in rendered
    assert "Elementos visibles en la pantalla actual" in rendered
    assert '[0] Button "Buscar" (clickable)' in rendered


def test_execute_command_conversational_turn_has_no_action():
    recognizer = FakeIntentRecognizer(
        IntentResult(
            action=Action(type=ActionType.NONE),
            reply="¡Hola! ¿En qué puedo ayudarte?",
            confidence=0.0,
        )
    )
    use_case = ExecuteCommandUseCase(intent_recognizer=recognizer)

    output = asyncio.run(use_case.execute(ExecuteCommandInputDTO(text="hola")))

    assert output.action_type == "NONE"
    assert output.parameters == {}
    assert output.success is True  # conversational reply still counts as handled
    assert output.requires_confirmation is False
