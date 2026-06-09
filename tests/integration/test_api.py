from fastapi import FastAPI
from fastapi.testclient import TestClient
from api.controllers import create_voice_router
from application.use_cases.transcribe_audio import TranscribeAudioUseCase
from application.use_cases.synthesize_speech import SynthesizeSpeechUseCase
from tests.fixtures.mocks import FakeSpeechToTextPort, FakeTextToSpeechPort


def create_test_app() -> FastAPI:
    app = FastAPI()
    transcribe_uc = TranscribeAudioUseCase(stt_port=FakeSpeechToTextPort())
    synthesize_uc = SynthesizeSpeechUseCase(tts_port=FakeTextToSpeechPort())
    app.include_router(create_voice_router(transcribe_uc, synthesize_uc))
    return app


def test_transcribe_endpoint():
    app = create_test_app()
    client = TestClient(app)
    files = {"audio_file": ("hello.wav", b"RIFFDATA", "audio/wav")}
    response = client.post("/voice/transcribe", files=files)

    assert response.status_code == 200
    assert response.json()["text"] == "Este es un texto simulado."


def test_synthesize_endpoint():
    app = create_test_app()
    client = TestClient(app)
    body = {"text": "Hola mundo", "voice": "alloy", "format": "mp3"}
    response = client.post("/voice/synthesize", json=body)

    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/mpeg"
    assert response.content == b"FAKEAUDIO"
