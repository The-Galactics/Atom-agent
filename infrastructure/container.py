from __future__ import annotations

from dataclasses import dataclass

from adapters.speech.faster_whisper_adapter import FasterWhisperAdapter
from adapters.speech.kokoro_adapter import KokoroAdapter
from adapters.llm.nvidia_gemma_adapter import NvidiaGemmaAdapter
from adapters.vector_store.qdrant_adapter import QdrantAdapter
from adapters.history.in_memory_history_adapter import InMemoryHistoryAdapter
from adapters.embeddings.bge_m3_adapter import BGEM3Adapter
from application.agents.nodes import GraphNodes
from application.agents.graph import build_graph
from application.use_cases.chat import ChatUseCase
from application.use_cases.synthesize_speech import SynthesizeSpeechUseCase
from application.use_cases.transcribe_audio import TranscribeAudioUseCase
from domain.value_objects import AudioFormat
from infrastructure.config import Settings
from infrastructure.provider_clients import KokoroClient


@dataclass
class AppContainer:
    settings: Settings
    kokoro_client: KokoroClient
    stt_adapter: FasterWhisperAdapter
    tts_adapter: KokoroAdapter
    llm_adapter: NvidiaGemmaAdapter
    vector_store: QdrantAdapter
    embedding_adapter: BGEM3Adapter
    history_adapter: InMemoryHistoryAdapter
    transcribe_use_case: TranscribeAudioUseCase
    synthesize_use_case: SynthesizeSpeechUseCase
    chat_use_case: ChatUseCase

    def shutdown(self) -> None:
        self.stt_adapter.shutdown()

    def readiness(self) -> dict:
        return {
            "status": "ok",
            "providers": {
                "stt": {
                    "status": "ready",
                    "provider": "faster_whisper",
                    "model": self.settings.faster_whisper_model,
                },
                "llm": {
                    "status": "ready" if self.settings.nvidia_api_key else "missing_key",
                    "provider": "nvidia/gemma",
                    "model": self.settings.llm_model,
                },
                "vector_store": {
                    "status": "ready",
                    "provider": "qdrant",
                    "url": self.settings.qdrant_url,
                }
            },
        }


def build_container(settings: Settings) -> AppContainer:
    kokoro_client = KokoroClient(
        endpoint=settings.kokoro_endpoint,
        api_key=settings.kokoro_api_key,
        timeout_seconds=settings.kokoro_timeout_seconds,
        max_retries=settings.kokoro_max_retries,
        retry_backoff_seconds=settings.kokoro_retry_backoff_seconds,
        model=settings.kokoro_model,
    )
    stt_adapter = FasterWhisperAdapter(
        model_name=settings.faster_whisper_model,
        device=settings.faster_whisper_device,
        compute_type=settings.faster_whisper_compute_type,
        max_concurrency=settings.max_stt_concurrency,
    )
    tts_adapter = KokoroAdapter(
        kokoro_client=kokoro_client,
        default_voice=settings.kokoro_default_voice,
        default_format=AudioFormat.from_string(settings.default_audio_format),
    )
    
    # Sprint 2 Components (Refactored)
    llm_adapter = NvidiaGemmaAdapter(
        api_key=settings.nvidia_api_key or "",
        model=settings.llm_model,
    )
    embedding_adapter = BGEM3Adapter(
        model_name=settings.embedding_model,
    )
    vector_store = QdrantAdapter(
        url=settings.qdrant_url,
        api_key=settings.qdrant_api_key,
        collection_name=settings.qdrant_collection,
        embedding_port=embedding_adapter,
    )
    history_adapter = InMemoryHistoryAdapter()
    
    nodes = GraphNodes(llm_adapter, vector_store)
    graph = build_graph(nodes)
    
    # Use Cases
    transcribe_use_case = TranscribeAudioUseCase(
        stt_port=stt_adapter,
        max_audio_payload_bytes=settings.max_audio_payload_bytes,
    )
    synthesize_use_case = SynthesizeSpeechUseCase(
        tts_port=tts_adapter,
        max_text_chars=settings.max_tts_text_chars,
        default_language=settings.default_language,
    )
    chat_use_case = ChatUseCase(
        graph=graph,
        history_adapter=history_adapter,
    )

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
    )
