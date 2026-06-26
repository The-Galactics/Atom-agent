"""Fail-fast startup probes.

A misconfigured LLM_MODEL otherwise fails silently on the first real request.
Probing once at boot gives an immediate startup failure for permanent config
errors. Transient LLM errors (rate limits, brief outages) are logged as
warnings so the process can start and degrade gracefully at request time.
"""
import logging

logger = logging.getLogger("voice_module")

_INVALID_MODEL_MARKERS = ("404", "not found")


def _is_invalid_model_error(exc: BaseException) -> bool:
    """Return True if *exc* signals a permanent invalid/unknown model id.

    Only 404 / "not found" are treated as fatal. The bare word "model" is
    deliberately excluded: a transient error (e.g. a 429/503 that names the
    model in its message) must degrade, not abort boot.
    """
    msg = str(exc).lower()
    return any(marker in msg for marker in _INVALID_MODEL_MARKERS)


async def probe_intent_model(recognizer) -> None:
    """Issue one trivial recognition to catch permanent model misconfiguration at boot.

    Raises RuntimeError if the probe error indicates an invalid model id (404 /
    "not found"). Transient errors (rate limits, timeouts, upstream 5xx) are
    logged as warnings and ignored — the request path already degrades
    gracefully when recognition fails.
    """
    if recognizer is None:
        return
    try:
        await recognizer.recognize("ping", session_id="__startup_probe__")
    except Exception as exc:  # noqa: BLE001
        if _is_invalid_model_error(exc):
            raise RuntimeError(
                f"LLM model probe failed — configured model may be invalid: {exc}"
            ) from exc
        logger.warning("startup_probe_degraded transient_error=%s", exc)
        return
    logger.info("startup_probe_ok intent_model")
