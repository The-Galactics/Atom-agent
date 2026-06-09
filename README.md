# Voice Module

Sprint 1 implements a standalone FastAPI voice module with hexagonal architecture:

- STT: Faster Whisper
- TTS: Kokoro HTTP endpoint
- API: FastAPI
- Tests: fake providers for unit/integration tests

## Structure

- `api/`: FastAPI controllers and schemas.
- `application/`: use cases and DTOs.
- `domain/`: pure models, value objects, and errors.
- `ports/`: STT, TTS, and optional audio storage contracts.
- `adapters/`: Faster Whisper, Kokoro, and fake provider implementations.
- `infrastructure/`: configuration, provider clients, composition root, logging.
- `tests/`: unit and integration tests.

## Configuration

Create a `.env` file or export these variables:

```bash
KOKORO_ENDPOINT=http://localhost:8880/v1/audio/speech
KOKORO_API_KEY=
KOKORO_DEFAULT_VOICE=af_heart
KOKORO_MODEL=kokoro
KOKORO_TIMEOUT_SECONDS=30
KOKORO_MAX_RETRIES=2
KOKORO_RETRY_BACKOFF_SECONDS=0.25

FASTER_WHISPER_MODEL=small
FASTER_WHISPER_DEVICE=cpu
FASTER_WHISPER_COMPUTE_TYPE=int8
MAX_STT_CONCURRENCY=1

DEFAULT_AUDIO_FORMAT=wav
DEFAULT_LANGUAGE=es
MAX_AUDIO_PAYLOAD_BYTES=10485760
MAX_TTS_TEXT_CHARS=1000
```

`KOKORO_ENDPOINT` must point to the full Kokoro speech endpoint. For common Kokoro FastAPI deployments, use `/v1/audio/speech`.

## Run

```bash
pip install -r requirements.txt
pip install faster-whisper
uvicorn main:app --reload
```

## API

```text
GET  /health
GET  /voice/health
POST /voice/transcribe
POST /voice/synthesize
```

STT supports these input MIME types:

```text
audio/wav
audio/x-wav
audio/flac
audio/ogg
```

TTS defaults to `audio/wav`.

See `ANDROID_CONTRACT.md` for the Android Java/OkHttp contract.

## Quick Checks

Transcribe:

```bash
curl -X POST http://localhost:8000/voice/transcribe \
  -H "X-Request-Id: local-test" \
  -F "file=@sample.wav;type=audio/wav" \
  -F "language=es" \
  -F "format=wav" \
  -F "beam_size=5"
```

Synthesize:

```bash
curl -X POST http://localhost:8000/voice/synthesize \
  -H "Content-Type: application/json" \
  -H "Accept: audio/wav" \
  -H "X-Request-Id: local-test" \
  -d '{"text":"Hola, soy tu asistente.","voice":"af_heart","language":"es","format":"wav","speed":1.0}' \
  --output speech.wav
```

## Tests

```bash
pytest
```

The default test suite uses fake STT/TTS providers and does not require Faster Whisper or Kokoro.
