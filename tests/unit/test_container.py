"""Unit tests for the dependency container wiring (``build_container``).

These run offline: ``voice_enabled=False`` skips the optional STT/TTS stack, the
Gemini adapters only build their SDK objects (no network at construction), and
Qdrant is lazy. ``_env_file=None`` isolates the tests from the developer's real
``.env`` so results are deterministic regardless of local secrets.
"""

from infrastructure.config import Settings
from infrastructure.container import build_container, _build_intent_use_case


def _settings(**overrides):
    base = dict(
        kokoro_endpoint="http://kokoro.invalid/v1",
        google_api_key="dummy-key",
        voice_enabled=False,
        llm_model="gemini-3.1-flash-lite",
    )
    base.update(overrides)
    # _env_file=None -> ignore the real .env so the test is hermetic.
    return Settings(_env_file=None, **base)


def test_build_container_wires_chat_and_intent_with_key():
    container = build_container(_settings())

    # Conversational + order paths are wired.
    assert container.chat_use_case is not None
    assert container.execute_command_use_case is not None

    # Voice disabled -> adapters and their use cases are absent (graceful).
    assert container.stt_adapter is None
    assert container.tts_adapter is None
    assert container.transcribe_use_case is None
    assert container.synthesize_use_case is None


def test_readiness_reflects_wiring():
    container = build_container(_settings())
    providers = container.readiness()["providers"]

    assert container.readiness()["status"] == "ok"
    assert providers["llm"]["status"] == "ready"
    assert providers["llm"]["model"] == "gemini-3.1-flash-lite"
    assert providers["intent"]["status"] == "ready"
    assert providers["voice"]["status"] == "degraded"


def test_shutdown_is_safe_without_voice_adapters():
    container = build_container(_settings())
    # stt_adapter is None -> shutdown must be a no-op, not an AttributeError.
    container.shutdown()


def test_intent_use_case_unavailable_without_api_key():
    use_case, status = _build_intent_use_case(
        _settings(google_api_key=None), chat_use_case=None
    )
    assert use_case is None
    assert "GOOGLE_API_KEY" in status


def test_build_container_degrades_without_api_key_instead_of_crashing():
    # Regression: an absent GOOGLE_API_KEY used to crash build_container because
    # the Gemini SDK rejects an empty key. It must now degrade gracefully.
    container = build_container(_settings(google_api_key=None))

    assert container.llm_adapter is None
    assert container.vector_store is None
    assert container.embedding_adapter is None
    assert container.chat_use_case is None
    assert container.execute_command_use_case is None
    assert "GOOGLE_API_KEY" in container.llm_status

    providers = container.readiness()["providers"]
    assert container.readiness()["status"] == "ok"
    assert providers["llm"]["status"] == "missing_key"
    assert providers["intent"]["status"] == "unavailable"
    # shutdown must still be safe with nothing wired.
    container.shutdown()
