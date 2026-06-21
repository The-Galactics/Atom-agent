import asyncio

from application.agents.session_store import SessionStore
from application.dtos import ExecuteCommandInputDTO
from application.use_cases.execute_command import ExecuteCommandUseCase
from domain.intent.models import Action, ActionType, IntentResult
from ports.intent_port import IntentRecognizerPort


class ScriptedRecognizer(IntentRecognizerPort):
    """Returns a queued IntentResult per call and records what it was passed.

    Accepts ``history`` so it exercises the orchestrator's ReAct chaining seam.
    """

    def __init__(self, results):
        self._results = list(results)
        self.calls = []  # list of dicts: {text, session_id, screen, history}

    async def recognize(self, text, session_id="default", screen=None, history=None):
        self.calls.append(
            {"text": text, "session_id": session_id, "screen": screen, "history": history}
        )
        return self._results.pop(0)


def _run(coro):
    return asyncio.run(coro)


def _open_app(app="youtube"):
    return IntentResult(
        action=Action(type=ActionType.OPEN_APP, parameters={"app_name": app}),
        reply="",
        confidence=1.0,
    )


def _tap(text="Buscar"):
    return IntentResult(
        action=Action(type=ActionType.TAP_ELEMENT, parameters={"text": text}),
        reply="",
        confidence=1.0,
        requires_confirmation=True,
    )


def _type_text(text="Rubius cartas Pokémon", submit=True):
    return IntentResult(
        action=Action(type=ActionType.TYPE_TEXT, parameters={"text": text, "submit": submit}),
        reply="",
        confidence=1.0,
    )


def _done(reply="Listo."):
    return IntentResult(
        action=Action(type=ActionType.NONE), reply=reply, confidence=0.0
    )


def test_tap_type_tap_sequence_not_collapsed_by_anti_repeat_guard():
    # Legitimate YouTube flow: tap(search) -> type_text -> tap(result). None of
    # these are identical (type or params differ), so the anti-repeat guard must
    # NOT mark any of them complete; all three steps accumulate.
    store = SessionStore(max_steps_per_session=20)
    recognizer = ScriptedRecognizer([_tap("Buscar"), _type_text(), _tap("Rubius - Cartas Pokémon")])
    use_case = ExecuteCommandUseCase(intent_recognizer=recognizer, session_store=store)

    out1 = _run(use_case.execute(ExecuteCommandInputDTO(text="busca", user_id="u")))
    assert out1.action_type == "TAP_ELEMENT"
    assert out1.task_complete is False

    out2 = _run(use_case.execute(ExecuteCommandInputDTO(text="busca", user_id="u")))
    assert out2.action_type == "TYPE_TEXT"
    assert out2.parameters == {"text": "Rubius cartas Pokémon", "submit": True}
    assert out2.task_complete is False

    out3 = _run(use_case.execute(ExecuteCommandInputDTO(text="busca", user_id="u")))
    assert out3.action_type == "TAP_ELEMENT"
    assert out3.task_complete is False
    assert len(store.get("u")) == 3


def test_multi_step_chain_accumulates_then_completes():
    store = SessionStore(max_steps_per_session=20)
    recognizer = ScriptedRecognizer([_open_app(), _tap(), _done("He buscado el vídeo.")])
    use_case = ExecuteCommandUseCase(intent_recognizer=recognizer, session_store=store)

    out1 = _run(use_case.execute(ExecuteCommandInputDTO(text="abre youtube y busca", user_id="u")))
    assert out1.action_type == "OPEN_APP"
    assert out1.step == 1
    assert out1.task_complete is False
    assert store.get("u") == ["Step 1: OPEN_APP {'app_name': 'youtube'}"]

    out2 = _run(use_case.execute(ExecuteCommandInputDTO(text="abre youtube y busca", user_id="u")))
    assert out2.action_type == "TAP_ELEMENT"
    assert out2.step == 2
    assert out2.task_complete is False
    assert len(store.get("u")) == 2

    out3 = _run(use_case.execute(ExecuteCommandInputDTO(text="abre youtube y busca", user_id="u")))
    assert out3.action_type == "NONE"
    assert out3.task_complete is True
    assert out3.reply_text == "He buscado el vídeo."
    # Session reset on completion.
    assert store.get("u") == []


def test_history_is_passed_to_recognizer_after_first_step():
    store = SessionStore()
    recognizer = ScriptedRecognizer([_open_app(), _tap()])
    use_case = ExecuteCommandUseCase(intent_recognizer=recognizer, session_store=store)

    _run(use_case.execute(ExecuteCommandInputDTO(text="cmd", user_id="u")))
    _run(use_case.execute(ExecuteCommandInputDTO(text="cmd", user_id="u")))

    # First call gets no history; second call gets the recorded Step 1.
    assert recognizer.calls[0]["history"] is None
    assert recognizer.calls[1]["history"] == ["Step 1: OPEN_APP {'app_name': 'youtube'}"]


def test_screen_elements_are_forwarded_each_step():
    store = SessionStore()
    recognizer = ScriptedRecognizer([_open_app(), _tap()])
    use_case = ExecuteCommandUseCase(intent_recognizer=recognizer, session_store=store)
    screen = [{"index": 0, "role": "Button", "text": "Buscar", "clickable": True}]

    _run(use_case.execute(ExecuteCommandInputDTO(text="cmd", user_id="u", screen_elements=screen)))
    _run(use_case.execute(ExecuteCommandInputDTO(text="cmd", user_id="u", screen_elements=screen)))

    assert recognizer.calls[0]["screen"] == screen
    assert recognizer.calls[1]["screen"] == screen


def test_single_transient_repeat_does_not_stop_the_loop():
    # One transient repeat (open_app re-emitted while the app is still launching
    # and the screen snapshot is stale) must NOT complete: only 2 identical in a
    # row, below the 3-in-a-row threshold. The loop continues.
    store = SessionStore()
    recognizer = ScriptedRecognizer([_open_app(), _open_app()])
    use_case = ExecuteCommandUseCase(intent_recognizer=recognizer, session_store=store)

    out1 = _run(use_case.execute(ExecuteCommandInputDTO(text="cmd", user_id="u")))
    assert out1.task_complete is False

    out2 = _run(use_case.execute(ExecuteCommandInputDTO(text="cmd", user_id="u")))
    assert out2.task_complete is False
    # The transient repeat IS recorded so the loop can keep progressing.
    assert len(store.get("u")) == 2


def test_three_identical_actions_in_a_row_stops_the_loop():
    # Three identical OPEN_APP in a row -> the third call is genuinely stuck and
    # must mark complete and stop (STUCK_REPEAT_THRESHOLD == 2 prior + current).
    store = SessionStore()
    recognizer = ScriptedRecognizer([_open_app(), _open_app(), _open_app()])
    use_case = ExecuteCommandUseCase(intent_recognizer=recognizer, session_store=store)

    out1 = _run(use_case.execute(ExecuteCommandInputDTO(text="cmd", user_id="u")))
    assert out1.task_complete is False

    out2 = _run(use_case.execute(ExecuteCommandInputDTO(text="cmd", user_id="u")))
    assert out2.task_complete is False
    assert len(store.get("u")) == 2

    out3 = _run(use_case.execute(ExecuteCommandInputDTO(text="cmd", user_id="u")))
    assert out3.task_complete is True
    # The repeated third action is not recorded and the session is reset.
    assert store.get("u") == []


def test_max_steps_cap_forces_graceful_completion():
    # Cap at 2: two executable actions, then the cap must force completion.
    store = SessionStore(max_steps_per_session=2)
    recognizer = ScriptedRecognizer([_open_app("a"), _open_app("b"), _open_app("c")])
    use_case = ExecuteCommandUseCase(
        intent_recognizer=recognizer, session_store=store, max_steps=2
    )

    out1 = _run(use_case.execute(ExecuteCommandInputDTO(text="cmd", user_id="u")))
    assert out1.task_complete is False
    assert out1.step == 1

    # Second executable action hits the cap -> forced completion.
    out2 = _run(use_case.execute(ExecuteCommandInputDTO(text="cmd", user_id="u")))
    assert out2.step == 2
    assert out2.task_complete is True
    assert out2.action_type == "OPEN_APP"
    # Reset on completion.
    assert store.get("u") == []


def test_first_turn_conversational_does_not_complete_task():
    # A pure greeting on the first call is single-shot, not a completed task.
    store = SessionStore()
    recognizer = ScriptedRecognizer([_done("¡Hola!")])
    use_case = ExecuteCommandUseCase(intent_recognizer=recognizer, session_store=store)

    out = _run(use_case.execute(ExecuteCommandInputDTO(text="hola", user_id="u")))

    assert out.action_type == "NONE"
    assert out.task_complete is False
    assert out.success is True
    assert store.get("u") == []


def test_sessions_are_isolated_by_user_id():
    store = SessionStore()
    recognizer = ScriptedRecognizer([_open_app("a"), _open_app("b")])
    use_case = ExecuteCommandUseCase(intent_recognizer=recognizer, session_store=store)

    _run(use_case.execute(ExecuteCommandInputDTO(text="cmd", user_id="u1")))
    out = _run(use_case.execute(ExecuteCommandInputDTO(text="cmd", user_id="u2")))

    # u2 starts fresh: step 1 with no history despite u1 having recorded a step.
    assert out.step == 1
    assert recognizer.calls[1]["history"] is None
    assert len(store.get("u1")) == 1
    assert len(store.get("u2")) == 1
