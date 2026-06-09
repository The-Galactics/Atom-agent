from fastapi import FastAPI
from domain.value_objects import AudioFormat
from infrastructure.config import get_settings
from infrastructure.provider_clients import KokoroClient
from adapters.faster_whisper_adapter import FasterWhisperAdapter
from adapters.kokoro_adapter import KokoroAdapter
from application.use_cases.transcribe_audio import TranscribeAudioUseCase
from application.use_cases.synthesize_speech import SynthesizeSpeechUseCase
from api.controllers import create_voice_router

settings = get_settings()

app = FastAPI(title="Voice Module", version="0.1.0")

@app.on_event("startup")
def startup_event() -> None:
    app.state.kokoro_client = KokoroClient(
        endpoint=settings.kokoro_endpoint,
        api_key=settings.kokoro_api_key,
        timeout_seconds=settings.kokoro_timeout_seconds,
    )
    app.state.faster_whisper_adapter = FasterWhisperAdapter(
        model_name=settings.faster_whisper_model,
        device=settings.faster_whisper_device,
    )
    app.state.kokoro_adapter = KokoroAdapter(
        kokoro_client=app.state.kokoro_client,
        default_voice=settings.kokoro_default_voice,
        default_format=AudioFormat.from_string(settings.default_audio_format),
    )
    app.state.transcribe_use_case = TranscribeAudioUseCase(
        stt_port=app.state.faster_whisper_adapter,
    )
    app.state.synthesize_use_case = SynthesizeSpeechUseCase(
        tts_port=app.state.kokoro_adapter,
    )

@app.on_event("shutdown")
def shutdown_event() -> None:
    if hasattr(app.state, "faster_whisper_adapter"):
        app.state.faster_whisper_adapter.shutdown()

app.include_router(
    create_voice_router(
        transcribe_use_case_provider=lambda: app.state.transcribe_use_case,
        synthesize_use_case_provider=lambda: app.state.synthesize_use_case,
    )
)
