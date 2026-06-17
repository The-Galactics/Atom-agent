import asyncio

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

    async def recognize(self, text: str, session_id: str = "default") -> IntentResult:
        self.last_text = text
        self.last_session = session_id
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
