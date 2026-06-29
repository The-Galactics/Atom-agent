"""Unit tests for ``CachingIntentRecognizer``.

Exercises the cache decorator with in-memory fakes (no Qdrant, no network):
first-step hit short-circuits the LLM; miss delegates and remembers only
cacheable actions; non-cacheable/sensitive actions and stale hits are ignored;
later ReAct steps bypass the cache; and a vector-store failure degrades to the
real recognizer instead of raising.
"""

import asyncio

from adapters.intent.caching_intent_recognizer import CachingIntentRecognizer
from domain.intent.models import Action, ActionType, IntentResult
from domain.memory.models import MemoryEntry
from ports.intent_port import IntentRecognizerPort
from ports.vector_store_port import VectorStorePort


class FakeRecognizer(IntentRecognizerPort):
    def __init__(self, result: IntentResult):
        self._result = result
        self.calls: list[dict] = []

    async def recognize(self, text, session_id="default", screen=None, history=None):
        self.calls.append(
            {"text": text, "session_id": session_id, "screen": screen, "history": history}
        )
        return self._result


class FakeVectorStore(VectorStorePort):
    def __init__(self, hits=None, search_exc=None):
        self._hits = hits or []
        self._search_exc = search_exc
        self.stored: list[tuple] = []
        self.search_calls = 0

    async def store(self, content, metadata):
        self.stored.append((content, metadata))

    async def search(self, query, limit=5, score_threshold=0.5):
        self.search_calls += 1
        if self._search_exc is not None:
            raise self._search_exc
        return self._hits


def _executable(action_type: ActionType, params=None, requires_confirmation=False):
    return IntentResult(
        action=Action(type=action_type, parameters=params or {}),
        reply="",
        confidence=1.0,
        requires_confirmation=requires_confirmation,
        raw_text="x",
    )


def _none_result():
    return IntentResult(
        action=Action(type=ActionType.NONE), reply="hola", confidence=0.0, raw_text="x"
    )


def _run_and_drain(rec: CachingIntentRecognizer, *args, **kwargs):
    """Run recognize and let any fire-and-forget _persist task finish."""
    async def go():
        result = await rec.recognize(*args, **kwargs)
        if rec._bg_tasks:
            await asyncio.gather(*list(rec._bg_tasks))
        return result

    return asyncio.run(go())


def test_first_step_hit_returns_cached_without_calling_llm():
    inner = FakeRecognizer(_executable(ActionType.OPEN_APP, {"app_name": "sentinel"}))
    store = FakeVectorStore(hits=[
        MemoryEntry(
            content="pon un temporizador de 5 minutos",
            metadata={
                "action_type": "SET_TIMER",
                "parameters_json": '{"duration_seconds": 300}',
                "requires_confirmation": False,
                "reply": "",
            },
            score=0.99,
        )
    ])
    rec = CachingIntentRecognizer(inner, store)

    result = _run_and_drain(rec, "pon un temporizador de 5 minutos")

    assert result.action.type is ActionType.SET_TIMER
    assert result.action.parameters == {"duration_seconds": 300}
    assert inner.calls == []  # LLM never called on a hit


def test_miss_delegates_and_remembers_cacheable_action():
    inner = FakeRecognizer(_executable(ActionType.OPEN_APP, {"app_name": "spotify"}))
    store = FakeVectorStore(hits=[])
    rec = CachingIntentRecognizer(inner, store)

    result = _run_and_drain(rec, "abre spotify")

    assert result.action.type is ActionType.OPEN_APP
    assert len(inner.calls) == 1
    assert len(store.stored) == 1
    text, meta = store.stored[0]
    assert text == "abre spotify"
    assert meta["action_type"] == "OPEN_APP"
    assert meta["parameters_json"] == '{"app_name": "spotify"}'


def test_non_cacheable_action_is_not_remembered():
    # TAP_ELEMENT is executable but screen-dependent -> never cached.
    inner = FakeRecognizer(_executable(ActionType.TAP_ELEMENT, {"text": "Aceptar"}))
    store = FakeVectorStore(hits=[])
    rec = CachingIntentRecognizer(inner, store)

    _run_and_drain(rec, "pulsa aceptar")

    assert store.stored == []


def test_sensitive_action_is_not_remembered():
    inner = FakeRecognizer(
        _executable(ActionType.MAKE_CALL, {"target": "mamá"}, requires_confirmation=True)
    )
    store = FakeVectorStore(hits=[])
    rec = CachingIntentRecognizer(inner, store)

    _run_and_drain(rec, "llama a mamá")

    assert store.stored == []


def test_history_present_bypasses_cache():
    inner = FakeRecognizer(_executable(ActionType.TYPE_TEXT, {"text": "audífonos"}))
    store = FakeVectorStore(hits=[])
    rec = CachingIntentRecognizer(inner, store)

    _run_and_drain(rec, "busca audífonos", history=["Step 1: OPEN_APP {'app_name': 'amazon'}"])

    assert store.search_calls == 0  # cache untouched mid-trajectory
    assert len(inner.calls) == 1
    assert inner.calls[0]["history"] is not None


def test_stale_or_unknown_cached_action_is_ignored():
    inner = FakeRecognizer(_none_result())
    store = FakeVectorStore(hits=[
        MemoryEntry(content="x", metadata={"action_type": "BOGUS_REMOVED",
                                           "parameters_json": "{}"}, score=0.99)
    ])
    rec = CachingIntentRecognizer(inner, store)

    result = _run_and_drain(rec, "haz algo raro")

    # Stale hit ignored -> delegated to the real recognizer.
    assert len(inner.calls) == 1
    assert result.action.type is ActionType.NONE


def test_lookup_failure_degrades_to_real_recognizer():
    inner = FakeRecognizer(_executable(ActionType.SET_ALARM, {"time": "07:00"}))
    store = FakeVectorStore(search_exc=RuntimeError("qdrant down"))
    rec = CachingIntentRecognizer(inner, store)

    result = _run_and_drain(rec, "pon una alarma a las 7")

    assert len(inner.calls) == 1  # no crash; fell through to the LLM
    assert result.action.type is ActionType.SET_ALARM
