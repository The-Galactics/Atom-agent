"""Caching decorator for the intent recognizer.

Wraps any :class:`IntentRecognizerPort` with a semantic cache (a vector store)
so that a *repeated, single-shot, screen-independent* command is resolved from
Qdrant without calling the LLM. This is the "method reuse" speed-up: frequent
quick orders ("pon un temporizador de 5 minutos", "linterna on", "abre spotify")
return instantly on a hit; everything else falls through to the real recognizer.

Deliberately conservative, by design:
  - Only the first ReAct step (``history`` empty) is cached. Later steps and any
    multi-step / screen-dependent flow always go to the LLM, so a cache hit can
    never replay a stale tap/scroll on a changed screen.
  - Only screen-independent, non-sensitive actions are cached (``_CACHEABLE``).
    Sensitive actions (calls, messages, taps) are never cached.
  - A high similarity threshold avoids returning a look-alike's action
    (e.g. "abre spotify" must not hit a cached "abre whatsapp").
It never blocks or deliberates: it is a single vector lookup, then either reuse
or delegate. Any vector-store failure degrades silently to the real recognizer.
"""

import asyncio
import json
import logging

from domain.intent.catalog import spec_for_type
from domain.intent.models import Action, ActionType, IntentResult
from infrastructure.observability.latency import timed
from ports.intent_port import IntentRecognizerPort
from ports.vector_store_port import VectorStorePort

logger = logging.getLogger("voice_module")

# Screen-independent, non-sensitive actions that are safe to reuse by language
# alone. Screen-dependent (navigate/scroll/read_screen/tap/type) and sensitive
# (call/message/tap) actions are intentionally excluded.
_CACHEABLE: frozenset[ActionType] = frozenset(
    {
        ActionType.OPEN_APP,
        ActionType.SET_ALARM,
        ActionType.SET_TIMER,
        ActionType.TOGGLE_SETTING,
    }
)


class CachingIntentRecognizer(IntentRecognizerPort):
    def __init__(
        self,
        inner: IntentRecognizerPort,
        vector_store: VectorStorePort,
        hit_threshold: float = 0.97,
    ):
        self._inner = inner
        self._store = vector_store
        self._hit_threshold = hit_threshold
        # Strong refs to fire-and-forget store tasks so they aren't GC'd.
        self._bg_tasks: set[asyncio.Task] = set()

    async def recognize(
        self, text: str, session_id: str = "default", screen=None, history=None
    ) -> IntentResult:
        # Cache only the first step of a task; later ReAct steps always use the
        # LLM (they depend on the live screen and the accumulated trace).
        if history:
            return await self._inner.recognize(
                text, session_id=session_id, screen=screen, history=history
            )

        with timed("skills.cache_lookup"):
            cached = await self._lookup(text)
        if cached is not None:
            logger.info("intent_cache_hit session_id=%s action=%s",
                        session_id, cached.action.type.value)
            return cached

        result = await self._inner.recognize(text, session_id=session_id, screen=screen)
        if result.action.is_executable and result.action.type in _CACHEABLE:
            self._remember(text, result)
        return result

    async def _lookup(self, text: str) -> IntentResult | None:
        """Return a cached IntentResult for ``text`` on a high-confidence hit."""
        try:
            entries = await self._store.search(
                text, limit=1, score_threshold=self._hit_threshold
            )
        except Exception as exc:  # best-effort: degrade to the real recognizer
            logger.warning("intent_cache_lookup_failed error=%s", exc)
            return None
        if not entries:
            return None

        meta = entries[0].metadata or {}
        action_type = ActionType.from_string(meta.get("action_type", ""))
        # Ignore stale/unsafe hits (action removed from the catalog, or a type
        # that should never be cached) — fall back to the LLM.
        if action_type not in _CACHEABLE or spec_for_type(action_type) is None:
            return None
        try:
            parameters = json.loads(meta.get("parameters_json") or "{}")
        except (ValueError, TypeError):
            return None
        return IntentResult(
            action=Action(type=action_type, parameters=parameters),
            reply=meta.get("reply", "") or "",
            confidence=1.0,
            requires_confirmation=bool(meta.get("requires_confirmation", False)),
            raw_text=text,
        )

    def _remember(self, text: str, result: IntentResult) -> None:
        """Persist the resolved action off the request path. Best-effort."""
        metadata = {
            "action_type": result.action.type.value,
            "parameters_json": json.dumps(result.action.parameters, ensure_ascii=False),
            "requires_confirmation": result.requires_confirmation,
            "reply": result.reply or "",
        }
        task = asyncio.create_task(self._persist(text, metadata))
        self._bg_tasks.add(task)
        task.add_done_callback(self._bg_tasks.discard)

    async def _persist(self, text: str, metadata: dict) -> None:
        try:
            await self._store.store(text, metadata)
        except Exception as exc:
            logger.warning("intent_cache_store_failed error=%s", exc)
