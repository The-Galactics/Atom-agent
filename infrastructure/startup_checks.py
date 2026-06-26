"""Fail-fast startup probes.

A misconfigured LLM_MODEL otherwise fails silently on the first real request.
Probing once at boot turns that into a loud, immediate startup failure.
"""
import logging

logger = logging.getLogger("voice_module")


async def probe_intent_model(recognizer) -> None:
    """Issue one trivial recognition so an invalid model id fails at boot.

    Raises RuntimeError (with the provider error chained) if the probe call
    cannot complete — e.g. the configured model id is not a real model.
    """
    try:
        await recognizer.recognize("ping", session_id="__startup_probe__")
    except Exception as exc:  # noqa: BLE001 - any failure here must stop startup
        raise RuntimeError(
            f"LLM model probe failed — configured model may be invalid: {exc}"
        ) from exc
    logger.info("startup_probe_ok intent_model")
