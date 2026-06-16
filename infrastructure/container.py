from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from adapters.speech.faster_whisper_adapter import FasterWhisperAdapter
from adapters.speech.kokoro_adapter import KokoroAdapter
from adapters.llm.gemini_adapter import GeminiAdapter
from adapters.embeddings.gemini_embedding_adapter import GeminiEmbeddingAdapter
from adapters.vector_store.qdrant_adapter import QdrantAdapter
from adapters.history.in_memory_history_adapter import InMemoryHistoryAdapter
from application.agents.nodes import GraphNodes
from application.agents.graph import build_graph
from application.use_cases.chat import ChatUseCase
from application.use_cases.synthesize_speech import SynthesizeSpeechUseCase
from application.use_cases.transcribe_audio import TranscribeAudioUseCase
from domain.value_objects import AudioFormat
from infrastructure.config import Settings
from infrastructure.provider_clients import KokoroClient

logger = logging.getLogger("voice_module")


@dataclass
class AppContainer:
    # Central dependency graph shared by the API layer.
    settings: Settings
    kokoro_client: Optional[KokoroClient]
    stt_adapter: Optional[FasterWhisperAdapter]
    tts_adapter: Optional[KokoroAdapter]
    llm_adapter: GeminiAdapter
    vector_store: QdrantAdapter
    embedding_adapter: GeminiEmbeddingAdapter
    history_adapter: InMemoryHistoryAdapter
    transcribe_use_case: Optional[TranscribeAudioUseCase]
    synthesize_use_case: Optional[SynthesizeSpeechUseCase]
    chat_use_case: ChatUseCase
    # Human-readable reason voice is unavailable, when applicable.
    voice_status: str = "ready"

    def shutdown(self) -> None:
        if self.stt_adapter is not None:
            self.stt_adapter.shutdown()

    def readiness(self) -> dict:
        voice_ready = self.transcribe_use_case is not None and self.synthesize_use_case is not None
        return {
            "status": "ok",
            "providers": {
                "stt": {
                    "status": "ready" if self.stt_adapter is not None else "unavailable",
                    "provider": "faster_whisper",
                    "model": self.settings.faster_whisper_model,
                    "detail": None if self.stt_adapter is not None else self.voice_status,
                },
                "tts": {
                    "status": "ready" if self.tts_adapter is not None else "unavailable",
                    "provider": "kokoro",
                    "endpoint": self.settings.kokoro_endpoint,
                    "detail": None if self.tts_adapter is not None else self.voice_status,
                },
                "voice": {
                    "status": "ready" if voice_ready else "degraded",
                    "detail": None if voice_ready else self.voice_status,
                },
                "llm": {
                    "status": "ready" if self.settings.google_api_key else "missing_key",
                    "provider": "google/gemini",
                    "model": self.settings.llm_model,
                },
                "vector_store": {
                    # Lazy + degrade-on-failure: reported "configured" since
                    # connectivity is only proven on first chat turn.
                    "status": "configured" if self.settings.memory_enabled else "disabled",
                    "provider": "qdrant",
                    "url": self.settings.qdrant_url,
                },
            },
        }


def _build_voice_adapters(settings: Settings):
    """Construct STT/TTS adapters defensively.

    Returns (kokoro_client, stt_adapter, tts_adapter, status). Any of the
    adapters may be ``None`` when the optional voice stack is unavailable
    (e.g. ``faster_whisper`` not installed) or disabled via config. ``status``
    is a human-readable reason used by readiness() and the voice error paths.
    """
    if not settings.voice_enabled:
        return None, None, None, "voice disabled via VOICE_ENABLED=false"

    kokoro_client = None
    stt_adapter = None
    tts_adapter = None
    status = "ready"

    try:
        kokoro_client = KokoroClient(
            endpoint=settings.kokoro_endpoint,
            api_key=settings.kokoro_api_key,
            timeout_seconds=settings.kokoro_timeout_seconds,
            max_retries=settings.kokoro_max_retries,
            retry_backoff_seconds=settings.kokoro_retry_backoff_seconds,
            model=settings.kokoro_model,
        )
        tts_adapter = KokoroAdapter(
            kokoro_client=kokoro_client,
            default_voice=settings.kokoro_default_voice,
            default_format=AudioFormat.from_string(settings.default_audio_format),
        )
    except Exception as exc:  # pragma: no cover - defensive
        status = f"tts provider unavailable: {exc}"
        logger.warning("tts_init_failed error=%s", exc)
        kokoro_client = None
        tts_adapter = None

    try:
        stt_adapter = FasterWhisperAdapter(
            model_name=settings.faster_whisper_model,
            device=settings.faster_whisper_device,
            compute_type=settings.faster_whisper_compute_type,
            max_concurrency=settings.max_stt_concurrency,
        )
    except Exception as exc:
        # Most commonly: faster_whisper optional dependency not installed.
        status = f"stt provider unavailable: {exc}"
        logger.warning("stt_init_failed error=%s", exc)
        stt_adapter = None

    return kokoro_client, stt_adapter, tts_adapter, status


def build_container(settings: Settings) -> AppContainer:
    kokoro_client, stt_adapter, tts_adapter, voice_status = _build_voice_adapters(settings)

    # Sprint 2 Components (Refactored). These construct cheaply now: the
    # embedding model and Qdrant connection are both lazy (loaded on first
    # use), so an unreachable Qdrant or undownloaded model never blocks boot.
    llm_adapter = GeminiAdapter(
        api_key=settings.google_api_key or "",
        model=settings.llm_model,
    )
    embedding_adapter = GeminiEmbeddingAdapter(
        api_key=settings.google_api_key or "",
        model=settings.embedding_model,
    )
    vector_store = QdrantAdapter(
        url=settings.qdrant_url,
        api_key=settings.qdrant_api_key,
        collection_name=settings.qdrant_collection,
        embedding_port=embedding_adapter,
    )
    history_adapter = InMemoryHistoryAdapter()

    nodes = GraphNodes(llm_adapter, vector_store, memory_enabled=settings.memory_enabled)
    graph = build_graph(nodes)

    # Voice use cases only exist when their adapters were constructed.
    transcribe_use_case = (
        TranscribeAudioUseCase(
            stt_port=stt_adapter,
            max_audio_payload_bytes=settings.max_audio_payload_bytes,
        )
        if stt_adapter is not None
        else None
    )
    synthesize_use_case = (
        SynthesizeSpeechUseCase(
            tts_port=tts_adapter,
            max_text_chars=settings.max_tts_text_chars,
            default_language=settings.default_language,
        )
        if tts_adapter is not None
        else None
    )
    chat_use_case = ChatUseCase(
        graph=graph,
        history_adapter=history_adapter,
    )

    if transcribe_use_case is None or synthesize_use_case is None:
        logger.warning("voice_degraded detail=%s", voice_status)

    return AppContainer(
        settings=settings,
        kokoro_client=kokoro_client,
        stt_adapter=stt_adapter,
        tts_adapter=tts_adapter,
        llm_adapter=llm_adapter,
        vector_store=vector_store,
        embedding_adapter=embedding_adapter,
        history_adapter=history_adapter,
        transcribe_use_case=transcribe_use_case,
        synthesize_use_case=synthesize_use_case,
        chat_use_case=chat_use_case,
        voice_status=voice_status,
    )
