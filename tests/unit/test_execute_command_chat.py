import asyncio
from application.agents.session_store import SessionStore
from application.use_cases.execute_command import ExecuteCommandUseCase
from application.dtos import ExecuteCommandInputDTO, ChatOutputDTO
from domain.intent.models import IntentResult, Action, ActionType
from ports.intent_port import IntentRecognizerPort


class FakeRecognizer(IntentRecognizerPort):
    def __init__(self, result):
        self._result = result

    async def recognize(self, text, session_id="default", screen=None, history=None):
        return self._result


class FakeChat:
    def __init__(self, text="REAL GROUNDED ANSWER", boom=False):
        self.text = text
        self.boom = boom
        self.calls = []

    async def execute(self, input_dto):
        self.calls.append(input_dto)
        if self.boom:
            raise RuntimeError("chat down")
        return ChatOutputDTO(text=self.text, session_id=input_dto.session_id)


def _conversational():
    return IntentResult(action=Action(type=ActionType.NONE), reply="stub reply", confidence=0.0)


def test_conversational_turn_returns_chat_answer():
    chat = FakeChat(text="Hola, soy la respuesta real.")
    uc = ExecuteCommandUseCase(intent_recognizer=FakeRecognizer(_conversational()), chat_use_case=chat)
    out = asyncio.run(uc.execute(ExecuteCommandInputDTO(text="hola", user_id="u1")))
    assert out.action_type == "NONE"
    assert out.reply_text == "Hola, soy la respuesta real."          # chat answer, not the stub
    assert chat.calls[0].text == "hola" and chat.calls[0].session_id == "u1"


def test_conversational_falls_back_to_recognizer_reply_on_chat_error():
    chat = FakeChat(boom=True)
    uc = ExecuteCommandUseCase(intent_recognizer=FakeRecognizer(_conversational()), chat_use_case=chat)
    out = asyncio.run(uc.execute(ExecuteCommandInputDTO(text="hola", user_id="u1")))
    assert out.reply_text == "stub reply"                            # graceful fallback


def test_conversational_without_chat_use_case_keeps_recognizer_reply():
    uc = ExecuteCommandUseCase(intent_recognizer=FakeRecognizer(_conversational()))  # no chat_use_case
    out = asyncio.run(uc.execute(ExecuteCommandInputDTO(text="hola", user_id="u1")))
    assert out.reply_text == "stub reply"


def test_executable_turn_does_not_call_chat():
    chat = FakeChat()
    open_app = IntentResult(action=Action(type=ActionType.OPEN_APP, parameters={"target": "spotify"}),
                            reply="", confidence=0.9)
    uc = ExecuteCommandUseCase(intent_recognizer=FakeRecognizer(open_app), chat_use_case=chat)
    out = asyncio.run(uc.execute(ExecuteCommandInputDTO(text="abre spotify", user_id="u1")))
    assert out.action_type == "OPEN_APP"
    assert chat.calls == []                                          # chat pipeline NOT invoked for actions


# ---------------------------------------------------------------------------
# FIX 1 regression test: ReAct completion turn must NOT call chat
# ---------------------------------------------------------------------------

class ScriptedRecognizer(IntentRecognizerPort):
    """Queued results; mirrors the one in test_react_orchestrator.py."""

    def __init__(self, results):
        self._results = list(results)
        self.calls = []

    async def recognize(self, text, session_id="default", screen=None, history=None):
        self.calls.append({"text": text, "session_id": session_id, "history": history})
        return self._results.pop(0)


def test_react_completion_skips_chat():
    """NONE turn after a prior action (completion) must NOT invoke the chat pipeline.

    Before FIX 1, the guard was ``action_type is NONE and chat_use_case is not None``,
    which would call chat on ANY NONE turn — including the ReAct completion summary.
    After the fix the guard also requires ``not history``.
    """
    chat = FakeChat(text="CHAT ANSWER THAT MUST NOT APPEAR")
    store = SessionStore(max_steps_per_session=20)
    recognizer = ScriptedRecognizer([
        # Turn 1: executable action → appended to history
        IntentResult(
            action=Action(type=ActionType.OPEN_APP, parameters={"app_name": "youtube"}),
            reply="",
            confidence=1.0,
        ),
        # Turn 2: NONE completion reply (history is non-empty at this point)
        IntentResult(
            action=Action(type=ActionType.NONE),
            reply="He terminado la tarea.",
            confidence=0.0,
        ),
    ])
    uc = ExecuteCommandUseCase(
        intent_recognizer=recognizer, session_store=store, chat_use_case=chat
    )

    # Step 1 — executable action, chat must not be called
    out1 = asyncio.run(uc.execute(
        ExecuteCommandInputDTO(text="abre youtube", user_id="u1", order_id="order-rc")
    ))
    assert out1.action_type == "OPEN_APP"
    assert out1.task_complete is False
    assert chat.calls == []

    # Step 2 — completion turn (NONE + non-empty history): chat must still not be called
    out2 = asyncio.run(uc.execute(
        ExecuteCommandInputDTO(text="continúa", user_id="u1", order_id="order-rc")
    ))
    assert out2.task_complete is True
    assert out2.action_type == "NONE"
    assert chat.calls == []                          # FIX 1: chat NOT called on completion turn
    assert out2.reply_text == "He terminado la tarea."   # recognizer summary preserved


def test_awaiting_confirmation_skips_chat():
    """A confirmation-hold turn returns structurally before the chat block.

    When a sensitive action is recognised the orchestrator calls set_pending and
    returns an awaiting_confirmation DTO immediately — the chat guard is never
    reached. This test pins that structural early-return so the guarantee is
    explicit and detectable by regression.
    """
    chat = FakeChat(text="SHOULD NOT APPEAR")
    store = SessionStore()
    send_msg = IntentResult(
        action=Action(
            type=ActionType.SEND_MESSAGE,
            parameters={"recipient": "mamá", "body": "Hola", "app": "whatsapp"},
        ),
        reply="",
        confidence=1.0,
        requires_confirmation=True,
    )
    recognizer = ScriptedRecognizer([send_msg])
    uc = ExecuteCommandUseCase(
        intent_recognizer=recognizer, session_store=store, chat_use_case=chat
    )

    out = asyncio.run(uc.execute(
        ExecuteCommandInputDTO(text="manda mensaje a mamá", user_id="u1", order_id="order-ac")
    ))
    assert out.awaiting_confirmation is True
    assert chat.calls == []     # confirmation hold returns early; chat never reached
