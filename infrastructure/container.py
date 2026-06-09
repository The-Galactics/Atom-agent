from __future__ import annotations

from dataclasses import dataclass

from adapters.faster_whisper_adapter import FasterWhisperAdapter
from adapters.kokoro_adapter import KokoroAdapter
from application.use_cases.synthesize_speech import SynthesizeSpeechUseCase
from application.use_cases.transcribe_audio import TranscribeAudioUseCase
from domain.value_objects import AudioFormat
from infrastructure.config import Settings
from infrastructure.provider_clients import KokoroClient


@dataclass
class VoiceContainer:
    settings: Settings
    kokoro_client: KokoroClient
    stt_adapter: FasterWhisperAdapter
    tts_adapter: KokoroAdapter
    transcribe_use_case: TranscribeAudioUseCase
    synthesize_use_case: SynthesizeSpeechUseCase

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
                    "device": self.settings.faster_whisper_device,
                },
                "tts": {
                    "status": "ready" if self.kokoro_client.health() else "degraded",
                    "provider": "kokoro",
                    "endpoint": self.settings.kokoro_endpoint,
                },
            },
        }


def build_container(settings: Settings) -> VoiceContainer:
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
    transcribe_use_case = TranscribeAudioUseCase(
        stt_port=stt_adapter,
        max_audio_payload_bytes=settings.max_audio_payload_bytes,
    )
    synthesize_use_case = SynthesizeSpeechUseCase(
        tts_port=tts_adapter,
        max_text_chars=settings.max_tts_text_chars,
        default_language=settings.default_language,
    )
    return VoiceContainer(
        settings=settings,
        kokoro_client=kokoro_client,
        stt_adapter=stt_adapter,
        tts_adapter=tts_adapter,
        transcribe_use_case=transcribe_use_case,
        synthesize_use_case=synthesize_use_case,
    )
