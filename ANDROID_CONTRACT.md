# Android Contract - Voice Module Sprint 1

This contract defines how the Java Android client sends audio to STT and text to TTS.

## Base URL

Use the backend URL configured for the running environment:

```text
http://<host>:<port>
```

## Common Headers

```http
X-Request-Id: <uuid>
Accept: application/json
```

`X-Request-Id` is recommended for tracing request logs across Android and backend.

## STT: Audio to Text

Endpoint:

```http
POST /voice/transcribe
Content-Type: multipart/form-data
Accept: application/json
```

Multipart fields:

| Field | Required | Type | Description |
|---|---:|---|---|
| `file` | yes | file | Audio payload. |
| `language` | no | string | `es`, `en`, or `auto`. |
| `format` | no | string | `wav`, `flac`, or `ogg`. |
| `beam_size` | no | int | Faster Whisper beam size, `1..10`. Default: `5`. |

Supported input MIME types:

```text
audio/wav
audio/x-wav
audio/flac
audio/ogg
```

Recommended Android recording format:

```text
WAV, mono, 16 kHz, PCM 16-bit
```

Successful response:

```json
{
  "text": "Hola, necesito que abras la camara.",
  "language": "es",
  "duration_seconds": 2.41,
  "confidence": 0.96,
  "provider": "faster_whisper"
}
```

Java/OkHttp example:

```java
OkHttpClient client = new OkHttpClient.Builder()
    .callTimeout(java.time.Duration.ofSeconds(10))
    .build();

File audio = new File(context.getCacheDir(), "command.wav");
RequestBody audioBody = RequestBody.create(audio, MediaType.parse("audio/wav"));

RequestBody body = new MultipartBody.Builder()
    .setType(MultipartBody.FORM)
    .addFormDataPart("file", "command.wav", audioBody)
    .addFormDataPart("language", "es")
    .addFormDataPart("format", "wav")
    .addFormDataPart("beam_size", "5")
    .build();

Request request = new Request.Builder()
    .url(baseUrl + "/voice/transcribe")
    .header("Accept", "application/json")
    .header("X-Request-Id", java.util.UUID.randomUUID().toString())
    .post(body)
    .build();

try (Response response = client.newCall(request).execute()) {
    if (!response.isSuccessful()) {
        throw new IOException("Unexpected HTTP " + response.code());
    }
    String json = response.body().string();
}
```

## TTS: Text to Audio

Endpoint:

```http
POST /voice/synthesize
Content-Type: application/json
Accept: audio/wav
```

JSON body:

```json
{
  "text": "Hola, soy tu asistente.",
  "voice": "af_heart",
  "language": "es",
  "format": "wav",
  "speed": 1.0
}
```

Fields:

| Field | Required | Type | Description |
|---|---:|---|---|
| `text` | yes | string | Text to synthesize. Max default: 1000 chars. |
| `voice` | no | string | Kokoro voice. Default comes from backend settings. |
| `language` | no | string | Default: `es`. |
| `format` | no | string | `wav`, `mp3`, `ogg`, or `flac`. Default: `wav`. |
| `speed` | no | number | `0.75..1.25`. Default: `1.0`. |

Successful response:

```http
HTTP/1.1 200 OK
Content-Type: audio/wav
Content-Disposition: inline; filename="speech.wav"
X-Request-Id: <uuid>
```

Body: binary audio bytes.

Java/OkHttp example:

```java
OkHttpClient client = new OkHttpClient.Builder()
    .callTimeout(java.time.Duration.ofSeconds(10))
    .build();

String json = "{"
    + "\"text\":\"Hola, soy tu asistente.\","
    + "\"voice\":\"af_heart\","
    + "\"language\":\"es\","
    + "\"format\":\"wav\","
    + "\"speed\":1.0"
    + "}";

RequestBody body = RequestBody.create(json, MediaType.parse("application/json"));

Request request = new Request.Builder()
    .url(baseUrl + "/voice/synthesize")
    .header("Accept", "audio/wav")
    .header("X-Request-Id", java.util.UUID.randomUUID().toString())
    .post(body)
    .build();

try (Response response = client.newCall(request).execute()) {
    if (!response.isSuccessful()) {
        throw new IOException("Unexpected HTTP " + response.code());
    }
    byte[] audioBytes = response.body().bytes();
}
```

## Error Shape

Errors returned by domain/application/provider handling use this shape:

```json
{
  "detail": {
    "error": {
      "code": "VALIDATION_ERROR",
      "message": "Unsupported audio mime type: audio/aac",
      "request_id": "uuid"
    }
  }
}
```

Expected statuses:

| Status | Meaning |
|---:|---|
| `400` | Invalid field value. |
| `413` | Payload too large. |
| `415` | Unsupported audio MIME type or requested audio format. |
| `422` | Malformed request handled by FastAPI/Pydantic. |
| `503` | Faster Whisper or Kokoro unavailable. |
| `500` | Unexpected server error. |

## Health Checks

```http
GET /health
GET /voice/health
```

`/health` checks the API process. `/voice/health` checks provider readiness.
