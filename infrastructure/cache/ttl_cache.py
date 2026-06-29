"""Tiny dependency-free per-key TTL cache (single-process). Not thread-safe by
design — used from the asyncio event loop only."""
import time


class TtlCache:
    def __init__(self, ttl_seconds, clock=time.monotonic):
        self._ttl = ttl_seconds
        self._clock = clock
        self._store = {}  # key -> (value, stored_at)

    def get(self, key):
        entry = self._store.get(key)
        if entry is None:
            return None
        value, stored_at = entry
        if self._clock() - stored_at >= self._ttl:
            self._store.pop(key, None)
            return None
        return value

    def put(self, key, value):
        self._store[key] = (value, self._clock())

    def invalidate(self, key):
        self._store.pop(key, None)
