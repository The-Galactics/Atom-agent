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

    def _now(self) -> float:
        return time.monotonic()

    def _evict_expired(self) -> None:
        if self._ttl <= 0:
            return
        cutoff = self._now() - self._ttl
        expired = [sid for sid, (_, ts) in self._sessions.items() if ts < cutoff]
        for sid in expired:
            del self._sessions[sid]

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
        """Drop the trace for ``session_id`` (called on task completion)."""
        self._sessions.pop(session_id, None)
