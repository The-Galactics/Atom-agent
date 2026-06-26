import asyncio
import pytest

from infrastructure.startup_checks import probe_intent_model


class _OkRecognizer:
    async def recognize(self, text, session_id="default", screen=None, history=None):
        return object()


class _BadRecognizer:
    async def recognize(self, text, session_id="default", screen=None, history=None):
        raise ValueError("404 model not found: gemini-3.1-flash-lite")


def test_probe_passes_for_working_model():
    asyncio.run(probe_intent_model(_OkRecognizer()))  # must not raise


def test_probe_raises_clear_error_on_bad_model():
    with pytest.raises(RuntimeError, match="model probe failed"):
        asyncio.run(probe_intent_model(_BadRecognizer()))
