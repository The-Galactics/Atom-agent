"""In-process sliding-window rate limiter (Fase 2A.3).

Dependency-free so it works in a single-instance deployment and in tests
without extra services. For a multi-instance deployment, swap this for a
Redis-backed limiter behind the same ``allow(key)`` interface.
"""

import time
from collections import defaultdict, deque
from collections.abc import Callable


class SlidingWindowRateLimiter:
    def __init__(
        self,
        max_requests: int,
        window_seconds: float,
        clock: Callable[[], float] = time.monotonic,
    ):
        self._max = max_requests
        self._window = window_seconds
        self._clock = clock
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str) -> bool:
        """Record a hit for ``key`` and return whether it is within the limit."""
        now = self._clock()
        cutoff = now - self._window
        hits = self._hits[key]
        while hits and hits[0] <= cutoff:
            hits.popleft()
        if len(hits) >= self._max:
            return False
        hits.append(now)
        return True
