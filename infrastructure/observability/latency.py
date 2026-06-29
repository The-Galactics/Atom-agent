"""Lightweight latency instrumentation: log one structured line per timed span.

Always-on at INFO under the `atom.latency` logger so spans are greppable
(`ATOM_LATENCY label=... ms=...`) without an external metrics system.
"""
import logging
import time
from contextlib import contextmanager

logger = logging.getLogger("atom.latency")


@contextmanager
def timed(label, clock=time.monotonic):
    start = clock()
    try:
        yield
    finally:
        elapsed_ms = (clock() - start) * 1000.0
        logger.info("ATOM_LATENCY label=%s ms=%.1f", label, elapsed_ms)
