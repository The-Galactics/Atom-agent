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
from application.use_cases.execute_command import ExecuteCommandUseCase
from application.use_cases.synthesize_speech import SynthesizeSpeechUseCase
from application.use_cases.transcribe_audio import TranscribeAudioUseCase
from domain.value_objects import AudioFormat
from infrastructure.config import Settings
from infrastructure.provider_clients import KokoroClient
from ports.stt_port import SpeechToTextPort
from ports.tts_port import TextToSpeechPort
from ports.llm_port import LLMPort
from ports.vector_store_port import VectorStorePort
from ports.embedding_port import EmbeddingPort
from ports.history_port import HistoryPort

logger = logging.getLogger("voice_module")


@dataclass
class AppContainer:
    # Central dependency graph shared by the API layer.
    settings: Settings
    kokoro_client: Optional[KokoroClient]
    stt_adapter: Optional[SpeechToTextPort]
    tts_adapter: Optional[TextToSpeechPort]
    # LLM/memory/chat stack. All None when the Gemini provider can't be built
    # (missing GOOGLE_API_KEY or SDK validation error) so startup degrades to
    # voice/health endpoints instead of crashing.
    llm_adapter: Optional[LLMPort]
    vector_store: Optional[VectorStorePort]
    embedding_adapter: Optional[EmbeddingPort]
    history_adapter: HistoryPort
    transcribe_use_case: Optional[TranscribeAudioUseCase]
    synthesize_use_case: Optional[SynthesizeSpeechUseCase]
    chat_use_case: Optional[ChatUseCase]
    # Order/intent path. None when the function-calling stack is unavailable.
    execute_command_use_case: Optional[ExecuteCommandUseCase] = None
    # Human-readable reason voice is unavailable, when applicable.
    voice_status: str = "ready"
    # Human-readable reason the intent stack is unavailable, when applicable.
    intent_status: str = "ready"
    # Human-readable reason the LLM/chat stack is unavailable, when applicable.
    llm_status: str = "ready"

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
                    "status": (
                        "ready" if self.llm_adapter is not None
                        else "missing_key" if not self.settings.google_api_key
                        else "unavailable"
                    ),
                    "provider": "google/gemini",
                    "model": self.settings.llm_model,
                    "detail": None if self.llm_adapter is not None else self.llm_status,
                },
                "intent": {
                    "status": "ready" if self.execute_command_use_case is not None else "unavailable",
                    "provider": "google/gemini-function-calling",
                    "detail": None if self.execute_command_use_case is not None else self.intent_status,
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


def _build_intent_use_case(settings: Settings, chat_use_case: ChatUseCase):
    """Construct the order/intent use case defensively.

    Returns (use_case, status). ``use_case`` is ``None`` when the function-
    calling provider can't be built (missing ``langchain-google-genai``,
    absent API key, etc.), so the order endpoint degrades gracefully. The chat
    use case is injected so conversational (non-action) utterances are answered
    by the grounded chat path instead of the router's context-free reply.
    """
    if not settings.google_api_key:
        return None, "intent provider unavailable: GOOGLE_API_KEY not set"
    try:
        from adapters.intent.gemini_function_calling_adapter import (
            GeminiFunctionCallingAdapter,
        )

        recognizer = GeminiFunctionCallingAdapter(
            api_key=settings.google_api_key,
            model=settings.llm_model,
            timezone=settings.assistant_timezone,
        )
        use_case = ExecuteCommandUseCase(
            intent_recognizer=recognizer,
            chat_use_case=chat_use_case,
        )
        return use_case, "ready"
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("intent_init_failed error=%s", exc)
        return None, f"intent provider unavailable: {exc}"


def _build_llm_stack(settings: Settings, history_adapter: HistoryPort):
    """Construct the LLM + semantic-memory + chat stack defensively.

    Returns ``(llm_adapter, embedding_adapter, vector_store, chat_use_case,
    status)``. All adapters are ``None`` when the Gemini provider can't be built
    — no ``GOOGLE_API_KEY`` or an SDK validation error — so the service degrades
    to voice/health endpoints instead of crashing at startup. The embedding
    model and Qdrant are lazy (connected on first use), so construction is cheap.
    """
    if not settings.google_api_key:
        return None, None, None, None, "llm provider unavailable: GOOGLE_API_KEY not set"
    try:
        llm_adapter = GeminiAdapter(
            api_key=settings.google_api_key,
            model=settings.llm_model,
            web_search=settings.web_search_enabled,
        )
        embedding_adapter = GeminiEmbeddingAdapter(
            api_key=settings.google_api_key,
            model=settings.embedding_model,
        )
        vector_store = QdrantAdapter(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key,
            collection_name=settings.qdrant_collection,
            embedding_port=embedding_adapter,
            dedup_threshold=settings.memory_dedup_threshold,
            ttl_days=settings.memory_ttl_days,
            prune_every=settings.memory_prune_every,
            vector_size=settings.qdrant_vector_size,
        )
        nodes = GraphNodes(
            llm_adapter, vector_store,
            memory_enabled=settings.memory_enabled,
            memory_min_words=settings.memory_min_words,
            timezone=settings.assistant_timezone,
        )
        graph = build_graph(nodes)
        chat_use_case = ChatUseCase(graph=graph, history_adapter=history_adapter)
        return llm_adapter, embedding_adapter, vector_store, chat_use_case, "ready"
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("llm_init_failed error=%s", exc)
        return None, None, None, None, f"llm provider unavailable: {exc}"


def build_container(settings: Settings) -> AppContainer:
    kokoro_client, stt_adapter, tts_adapter, voice_status = _build_voice_adapters(settings)

    history_adapter = InMemoryHistoryAdapter(
        max_messages_per_session=settings.history_max_messages_per_session,
    )

    # Built defensively: degrades to None (not a crash) when GOOGLE_API_KEY is
    # absent or the Gemini SDK rejects the configuration.
    (
        llm_adapter,
        embedding_adapter,
        vector_store,
        chat_use_case,
        llm_status,
    ) = _build_llm_stack(settings, history_adapter)

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

    # Built defensively: degrades to UNAVAILABLE if the provider is misconfigured.
    # chat_use_case (possibly None) is injected so non-action utterances get the
    # grounded path when available, and degrade cleanly when it isn't.
    execute_command_use_case, intent_status = _build_intent_use_case(settings, chat_use_case)

    if transcribe_use_case is None or synthesize_use_case is None:
        logger.warning("voice_degraded detail=%s", voice_status)
    if chat_use_case is None:
        logger.warning("llm_degraded detail=%s", llm_status)
    if execute_command_use_case is None:
        logger.warning("intent_degraded detail=%s", intent_status)

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
        execute_command_use_case=execute_command_use_case,
        voice_status=voice_status,
        intent_status=intent_status,
        llm_status=llm_status,
    )
