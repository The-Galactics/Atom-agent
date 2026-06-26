import asyncio
import pytest

from infrastructure.startup_checks import probe_intent_model


class _OkRecognizer:
    async def recognize(self, text, session_id="default", screen=None, history=None):
        return object()


class _BadRecognizer:
    async def recognize(self, text, session_id="default", screen=None, history=None):
        raise ValueError("404 model not found: gemini-3.1-flash-lite")


class _TransientRecognizer:
    async def recognize(self, text, session_id="default", screen=None, history=None):
        raise TimeoutError("503 upstream temporarily unavailable")


class _RateLimitWithModelNameRecognizer:
    async def recognize(self, text, session_id="default", screen=None, history=None):
        raise RuntimeError("429 quota exceeded for model gemini-3.1-flash in region us-east1")


def test_probe_passes_for_working_model():
    asyncio.run(probe_intent_model(_OkRecognizer()))  # must not raise


def test_probe_raises_clear_error_on_bad_model():
    with pytest.raises(RuntimeError, match="model probe failed"):
        asyncio.run(probe_intent_model(_BadRecognizer()))


def test_probe_degrades_on_transient_error():
    # A transient error (timeout, 5xx) must NOT abort startup.
    asyncio.run(probe_intent_model(_TransientRecognizer()))  # must not raise


def test_probe_does_nothing_when_recognizer_is_none():
    asyncio.run(probe_intent_model(None))  # must not raise


def test_probe_degrades_on_rate_limit_mentioning_model_name():
    # A transient 429 whose message names the model must NOT be misread as a
    # fatal invalid-model error: the bare "model" marker was over-broad.
    asyncio.run(probe_intent_model(_RateLimitWithModelNameRecognizer()))  # must not raise
