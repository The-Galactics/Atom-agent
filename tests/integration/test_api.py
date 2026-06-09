from fastapi import FastAPI
import pytest
from httpx import ASGITransport, AsyncClient
from api.controllers import create_voice_router
from application.use_cases.transcribe_audio import TranscribeAudioUseCase
from application.use_cases.synthesize_speech import SynthesizeSpeechUseCase
from tests.fixtures.mocks import FakeSpeechToTextPort, FakeTextToSpeechPort


@pytest.fixture
def anyio_backend():
    return "asyncio"


def create_test_app() -> FastAPI:
    app = FastAPI()
    transcribe_uc = TranscribeAudioUseCase(stt_port=FakeSpeechToTextPort())
    synthesize_uc = SynthesizeSpeechUseCase(tts_port=FakeTextToSpeechPort())
    app.include_router(
        create_voice_router(
            transcribe_uc,
            synthesize_uc,
            readiness_provider=lambda: {"status": "ok"},
        )
    )
    return app


@pytest.mark.anyio
async def test_transcribe_endpoint():
    app = create_test_app()
    files = {"file": ("hello.wav", b"RIFFDATA", "audio/wav")}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/voice/transcribe", files=files)

    assert response.status_code == 200
    assert response.json()["text"] == "Este es un texto simulado."


@pytest.mark.anyio
async def test_synthesize_endpoint():
    app = create_test_app()
    body = {"text": "Hola mundo", "voice": "af_heart", "format": "wav"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/voice/synthesize", json=body)

    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/wav"
    assert response.content == b"FAKEAUDIO"


@pytest.mark.anyio
async def test_health_endpoints():
    app = create_test_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/voice/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
