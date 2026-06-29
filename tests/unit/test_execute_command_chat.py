import asyncio
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
