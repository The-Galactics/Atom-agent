from __future__ import annotations

import time
from collections import OrderedDict


class SessionStore:
    """Bounded in-memory store of per-session ReAct action traces.

    Keyed by ``session_id``, each entry is an ordered list of rendered step
    strings (e.g. ``"Step 1: OPEN_APP {'app_name': 'youtube'}"``) that the
    orchestrator feeds back to the recognizer as evolving history. Pure and
    injectable: no external deps, trivially mockable.

    Eviction is bounded on three axes:
      - ``max_steps_per_session``: a session's trace never grows past this.
      - ``max_sessions``: least-recently-used session is dropped past this.
      - ``ttl_seconds``: sessions idle longer than this are pruned on access.
    """

    def __init__(
        self,
        max_steps_per_session: int = 20,
        max_sessions: int = 1000,
        ttl_seconds: float = 3600.0,
    ):
        self._max_steps = max_steps_per_session
        self._max_sessions = max_sessions
        self._ttl = ttl_seconds
        # session_id -> (steps, last_touch_monotonic)
        self._sessions: OrderedDict[str, tuple[list[str], float]] = OrderedDict()
        # session_id -> (pending_action, last_touch_monotonic). Holds a sensitive
        # action proposed but awaiting the user's spoken confirmation. Shares the
        # same TTL/LRU bounds as the trace so it can't grow unbounded.
        self._pending: OrderedDict[str, tuple[dict, float]] = OrderedDict()

    def _now(self) -> float:
        return time.monotonic()

    def _evict_expired(self) -> None:
        if self._ttl <= 0:
            return
        cutoff = self._now() - self._ttl
        expired = [sid for sid, (_, ts) in self._sessions.items() if ts < cutoff]
        for sid in expired:
            del self._sessions[sid]
        expired_pending = [sid for sid, (_, ts) in self._pending.items() if ts < cutoff]
        for sid in expired_pending:
            del self._pending[sid]

    def _touch(self, session_id: str) -> list[str]:
        steps, _ = self._sessions.pop(session_id, ([], 0.0))
        self._sessions[session_id] = (steps, self._now())
        self._sessions.move_to_end(session_id)
        return steps

    def get(self, session_id: str) -> list[str]:
        """Return a copy of the ordered action trace for ``session_id``."""
        self._evict_expired()
        if session_id not in self._sessions:
            return []
        return list(self._touch(session_id))

    def append(self, session_id: str, step: str) -> None:
        """Record one rendered step, enforcing per-session and LRU caps."""
        self._evict_expired()
        steps = self._touch(session_id)
        steps.append(step)
        if len(steps) > self._max_steps:
            del steps[: len(steps) - self._max_steps]
        self._sessions[session_id] = (steps, self._now())
        while len(self._sessions) > self._max_sessions:
            self._sessions.popitem(last=False)

    def reset(self, session_id: str) -> None:
        """Drop the trace AND any pending confirmation for ``session_id``."""
        self._sessions.pop(session_id, None)
        self._pending.pop(session_id, None)

    # --- Pending confirmation (conversational "ask first" flow) -------------

    def set_pending(
        self, session_id: str, action_type: str, parameters: dict, reasks: int = 0
    ) -> None:
        """Record a sensitive action awaiting the user's spoken confirmation."""
        self._evict_expired()
        pending = {
            "action_type": action_type,
            "parameters": dict(parameters or {}),
            "reasks": reasks,
        }
        self._pending[session_id] = (pending, self._now())
        self._pending.move_to_end(session_id)
        while len(self._pending) > self._max_sessions:
            self._pending.popitem(last=False)

    def get_pending(self, session_id: str) -> dict | None:
        """Return a copy of the pending action for ``session_id``, or None."""
        self._evict_expired()
        entry = self._pending.get(session_id)
        if entry is None:
            return None
        pending, _ = entry
        self._pending[session_id] = (pending, self._now())
        self._pending.move_to_end(session_id)
        # Deep-ish copy: callers must not mutate the stored action/parameters.
        copy = dict(pending)
        copy["parameters"] = dict(pending.get("parameters", {}))
        return copy

    def clear_pending(self, session_id: str) -> None:
        """Drop any pending confirmation for ``session_id``."""
        self._pending.pop(session_id, None)
