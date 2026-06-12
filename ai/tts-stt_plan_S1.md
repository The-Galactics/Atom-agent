# Arquitectura Sprint 1: Voice Module Hexagonal con FastAPI, Faster Whisper y Kokoro

## 1. Resumen

Construir un módulo independiente `voice-module` que expone dos capacidades:

- `Audio -> Texto`: Android envía audio, FastAPI invoca un caso de uso, el puerto STT delega en Faster Whisper, y se retorna transcripción estructurada.
- `Texto -> Audio`: Android envía texto, FastAPI invoca un caso de uso, el puerto TTS delega en Kokoro, y se retorna audio generado.

Principio central: el dominio y la aplicación no conocen Faster Whisper, Kokoro, FastAPI, archivos, HTTP ni Android. Solo conocen contratos internos.

```text
Android Java Client
        |
        | HTTP multipart/json
        v
FastAPI Adapter
        |
        | DTO/API -> Command
        v
Application Layer
        |
        | Use Cases
        v
Ports
   |                |
   v                v
STT Port        TTS Port
   |                |
   v                v
FasterWhisper   Kokoro
Adapter         Adapter
```

Flujo STT:

```text
Android
  -> POST /voice/transcribe multipart/form-data
  -> FastAPI Controller valida request HTTP
  -> TranscribeAudioUseCase valida reglas de aplicación
  -> SpeechToTextPort.transcribe(...)
  -> FasterWhisperSpeechToTextAdapter
  -> retorna TranscriptionResult
  -> FastAPI serializa JSON
  -> Android recibe texto
```

Flujo TTS:

```text
Android
  -> POST /voice/synthesize application/json
  -> FastAPI Controller valida request HTTP
  -> SynthesizeSpeechUseCase valida reglas de aplicación
  -> TextToSpeechPort.synthesize(...)
  -> KokoroTextToSpeechAdapter
  -> retorna SynthesizedSpeech
  -> FastAPI responde audio/wav o audio/mpeg
  -> Android reproduce audio
```

## 2. Arquitectura Hexagonal

Capas permitidas:

```text
api/adapters/infrastructure -> application -> domain
adapters -> ports
application -> ports + domain
domain -> nada externo
```

Dependencias prohibidas:

- `domain` no importa `fastapi`, `pydantic`, `faster_whisper`, `kokoro`, `torch`, `requests`, filesystem ni variables de entorno.
- `application` no instancia modelos Faster Whisper ni Kokoro.
- `ports` no dependen de implementaciones concretas.
- `api` no contiene lógica de transcripción ni síntesis.
- Los adapters no deben filtrar tipos propietarios hacia application/domain.

Responsabilidades:

- `domain`: conceptos puros del módulo de voz: audio, texto, idioma, resultado de transcripción, resultado de síntesis, errores de dominio.
- `application`: casos de uso, validaciones de negocio, orquestación, límites de tamaño/duración, selección de opciones.
- `ports`: contratos abstractos que la aplicación necesita.
- `adapters`: implementaciones concretas de puertos: Faster Whisper, Kokoro, mocks/fakes.
- `api`: entrada HTTP FastAPI, schemas HTTP, traducción de errores a status codes.
- `infrastructure`: configuración, logging, dependency injection, lifecycle de modelos, health checks.

## 3. Estructura de Proyecto

```text
voice-module/
├── src/
│   └── voice_module/
│       ├── domain/
│       │   ├── value_objects.py
│       │   ├── entities.py
│       │   └── errors.py
│       ├── application/
│       │   ├── use_cases/
│       │   │   ├── transcribe_audio.py
│       │   │   └── synthesize_speech.py
│       │   └── dto.py
│       ├── ports/
│       │   ├── speech_to_text.py
│       │   └── text_to_speech.py
│       ├── adapters/
│       │   ├── stt/
│       │   │   ├── faster_whisper_adapter.py
│       │   │   └── fake_stt_adapter.py
│       │   ├── tts/
│       │   │   ├── kokoro_adapter.py
│       │   │   └── fake_tts_adapter.py
│       │   └── api/
│       │       ├── routes.py
│       │       ├── schemas.py
│       │       └── error_handlers.py
│       ├── infrastructure/
│       │   ├── config.py
│       │   ├── container.py
│       │   ├── logging.py
│       │   └── model_lifecycle.py
│       └── main.py
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── contract/
│   └── fixtures/
├── pyproject.toml
├── requirements.txt
└── README.md
```

Responsabilidad por carpeta:

- `domain`: objetos inmutables, errores propios y reglas puras.
- `application`: comandos, respuestas y casos de uso.
- `ports`: interfaces que permiten sustituir proveedores.
- `adapters/stt`: Faster Whisper y dobles de prueba.
- `adapters/tts`: Kokoro y dobles de prueba.
- `adapters/api`: FastAPI como adapter de entrada.
- `infrastructure`: composición de dependencias, configuración y carga de modelos.
- `tests`: pruebas separadas por tipo para evitar depender de modelos reales en unit tests.

## 4. Modelo de Dominio

Dominio mínimo. No crear entidades artificiales.

Value Objects:

- `AudioContent`: bytes, mime type, sample rate opcional, filename opcional.
- `TextContent`: texto validado no vacío.
- `LanguageCode`: código ISO simple, por ejemplo `es`, `en`, `auto`.
- `VoiceId`: identificador de voz para Kokoro.
- `AudioFormat`: `wav`, `mp3`, `pcm`.
- `TranscriptionResult`: texto, idioma detectado, duración, segmentos opcionales.
- `SynthesizedSpeech`: bytes de audio, mime type, duración estimada, formato.

Entidades:

- No se necesita entidad persistente en Sprint 1.
- No modelar `User`, `Conversation`, `Memory` ni `Agent`.

DTOs:

- API DTOs viven en `adapters/api/schemas.py`.
- Application DTOs viven en `application/dto.py`.
- Dominio no usa Pydantic.

Casos de uso:

- `TranscribeAudioUseCase`
- `SynthesizeSpeechUseCase`

Errores del dominio/aplicación:

- `InvalidAudioError`
- `UnsupportedAudioFormatError`
- `AudioTooLargeError`
- `EmptyTextError`
- `TextTooLongError`
- `ProviderUnavailableError`
- `VoiceSynthesisError`
- `SpeechRecognitionError`

## 5. Puertos

### SpeechToTextPort

```python
from abc import ABC, abstractmethod
from voice_module.domain.value_objects import AudioContent, LanguageCode
from voice_module.domain.entities import TranscriptionResult

class SpeechToTextPort(ABC):
    @abstractmethod
    async def transcribe(
        self,
        audio: AudioContent,
        language: LanguageCode | None = None,
        beam_size: int = 5,
    ) -> TranscriptionResult:
        """Transcribe audio into text.

        Contract:
        - Must not return provider-specific objects.
        - Must raise SpeechRecognitionError or ProviderUnavailableError.
        - Must support language=None or auto-detection.
        """
```

### TextToSpeechPort

```python
from abc import ABC, abstractmethod
from voice_module.domain.value_objects import TextContent, VoiceId, AudioFormat, LanguageCode
from voice_module.domain.entities import SynthesizedSpeech

class TextToSpeechPort(ABC):
    @abstractmethod
    async def synthesize(
        self,
        text: TextContent,
        voice: VoiceId,
        language: LanguageCode,
        audio_format: AudioFormat,
        speed: float = 1.0,
    ) -> SynthesizedSpeech:
        """Generate speech audio from text.

        Contract:
        - Must return bytes and MIME type.
        - Must not leak Kokoro-specific types.
        - Must raise VoiceSynthesisError or ProviderUnavailableError.
        """
```

### AudioStoragePort

No incluir en Sprint 1 por defecto. Solo agregarlo si se decide guardar audios temporalmente fuera de memoria. Para Sprint 1, usar memoria y límites estrictos de tamaño.

## 6. Adapters

### FasterWhisperSpeechToTextAdapter

Responsabilidades:

- Cargar `WhisperModel` una sola vez durante lifecycle.
- Convertir `AudioContent` a formato aceptado por Faster Whisper.
- Ejecutar transcripción.
- Mapear segmentos del proveedor a `TranscriptionResult`.
- Convertir errores técnicos en errores del módulo.

Decisión de implementación:

- Modelo inicial recomendado para objetivo <3s: `base` o `small`, configurable por env.
- `compute_type`: `int8` en CPU, `float16` si GPU disponible.
- No cargar modelo por request.

### KokoroTextToSpeechAdapter

Responsabilidades:

- Cargar pipeline/modelo Kokoro una sola vez.
- Validar voz soportada desde configuración.
- Generar audio.
- Serializar a `wav` por defecto.
- Mapear errores a `VoiceSynthesisError`.

Decisión de implementación:

- Formato default para Android: `audio/wav`.
- Voz default configurable, por ejemplo `af_heart` o la voz disponible en instalación.
- `speed` permitido: `0.75` a `1.25`.

### FastAPI Adapter

Responsabilidades:

- Recibir HTTP.
- Validar tamaño, content type, campos requeridos.
- Convertir request HTTP a command de aplicación.
- Ejecutar use case.
- Traducir respuesta a JSON/audio.
- Traducir errores a HTTP.

No debe:

- Instanciar Faster Whisper o Kokoro directamente.
- Contener reglas de negocio.
- Parsear resultados internos de proveedores.

## 7. Casos de Uso

### TranscribeAudioUseCase

Input:

```python
@dataclass(frozen=True)
class TranscribeAudioCommand:
    audio_bytes: bytes
    mime_type: str
    filename: str | None = None
    language: str | None = None
    beam_size: int = 5
```

Output:

```python
@dataclass(frozen=True)
class TranscribeAudioResponse:
    text: str
    language: str | None
    duration_seconds: float | None
    segments: list[dict]
```

Validaciones:

- `audio_bytes` no vacío.
- Tamaño máximo: default `10 MB`.
- MIME permitido: `audio/wav`, `audio/mpeg`, `audio/mp4`, `audio/webm`, `audio/x-wav`.
- `beam_size` entre `1` y `10`.
- `language` opcional; si viene, debe ser código simple.
- No aceptar audio arbitrario sin content type.

Flujo interno:

```text
1. Validar comando.
2. Crear AudioContent.
3. Crear LanguageCode si aplica.
4. Invocar SpeechToTextPort.transcribe.
5. Validar que el texto resultante no sea None.
6. Retornar TranscribeAudioResponse.
```

### SynthesizeSpeechUseCase

Input:

```python
@dataclass(frozen=True)
class SynthesizeSpeechCommand:
    text: str
    voice: str | None = None
    language: str = "es"
    audio_format: str = "wav"
    speed: float = 1.0
```

Output:

```python
@dataclass(frozen=True)
class SynthesizeSpeechResponse:
    audio_bytes: bytes
    mime_type: str
    filename: str
    duration_seconds: float | None
```

Validaciones:

- Texto no vacío después de `strip`.
- Longitud máxima default: `1000` caracteres.
- `audio_format` permitido: `wav` en Sprint 1; `mp3` opcional si se implementa codificación.
- `speed` entre `0.75` y `1.25`.
- `voice` default desde configuración.
- `language` default `es`.

Flujo interno:

```text
1. Validar comando.
2. Crear TextContent, VoiceId, LanguageCode y AudioFormat.
3. Invocar TextToSpeechPort.synthesize.
4. Validar bytes generados no vacíos.
5. Retornar audio con MIME correcto.
```

## 8. API Design

### POST `/voice/transcribe`

Request:

- `multipart/form-data`
- Campo `file`: audio.
- Campo opcional `language`: `es`, `en` o `auto`.
- Campo opcional `beam_size`: entero.

Headers recomendados:

```http
Content-Type: multipart/form-data
Accept: application/json
X-Request-Id: <uuid>
```

Ejemplo request conceptual:

```text
file=@audio.wav
language=es
beam_size=5
```

Response `200`:

```json
{
  "text": "Hola, necesito que abras la cámara.",
  "language": "es",
  "duration_seconds": 2.41,
  "segments": [
    {
      "start": 0.0,
      "end": 2.41,
      "text": "Hola, necesito que abras la cámara."
    }
  ]
}
```

Errores:

- `400`: audio vacío, texto inválido, parámetros inválidos.
- `413`: audio supera tamaño máximo.
- `415`: MIME no soportado.
- `422`: request mal formado.
- `503`: proveedor STT no disponible.
- `500`: error inesperado.

Error shape:

```json
{
  "error": {
    "code": "UNSUPPORTED_AUDIO_FORMAT",
    "message": "Audio MIME type is not supported.",
    "request_id": "uuid"
  }
}
```

### POST `/voice/synthesize`

Request:

```http
Content-Type: application/json
Accept: audio/wav
X-Request-Id: <uuid>
```

Body:

```json
{
  "text": "Hola, soy tu asistente.",
  "voice": "default",
  "language": "es",
  "format": "wav",
  "speed": 1.0
}
```

Response `200`:

```http
Content-Type: audio/wav
Content-Disposition: inline; filename="speech.wav"
X-Audio-Duration-Seconds: 1.72
```

Body: bytes de audio.

Errores:

- `400`: texto vacío, voz inválida, velocidad inválida.
- `413`: texto demasiado largo.
- `415`: formato de audio no soportado.
- `503`: proveedor TTS no disponible.
- `500`: error inesperado.

Endpoint adicional recomendado:

```text
GET /health
GET /voice/health
```

`/health` valida que la API está viva. `/voice/health` valida readiness de modelos STT/TTS.

## 9. Diagramas de Secuencia

Audio a texto:

```text
Android Java Client
    |
    | POST /voice/transcribe multipart
    v
FastAPI Route
    |
    | creates TranscribeAudioCommand
    v
TranscribeAudioUseCase
    |
    | validates input
    | creates AudioContent
    v
SpeechToTextPort
    |
    | implemented by
    v
FasterWhisperSpeechToTextAdapter
    |
    | model.transcribe(audio)
    v
Faster Whisper
    |
    | segments + language
    v
FasterWhisperSpeechToTextAdapter
    |
    | maps provider output
    v
TranscribeAudioUseCase
    |
    | TranscribeAudioResponse
    v
FastAPI Route
    |
    | JSON 200
    v
Android Java Client
```

Texto a audio:

```text
Android Java Client
    |
    | POST /voice/synthesize JSON
    v
FastAPI Route
    |
    | creates SynthesizeSpeechCommand
    v
SynthesizeSpeechUseCase
    |
    | validates text, voice, speed
    v
TextToSpeechPort
    |
    | implemented by
    v
KokoroTextToSpeechAdapter
    |
    | generate waveform
    v
Kokoro
    |
    | audio samples
    v
KokoroTextToSpeechAdapter
    |
    | encodes WAV
    v
SynthesizeSpeechUseCase
    |
    | SynthesizeSpeechResponse
    v
FastAPI Route
    |
    | audio/wav 200
    v
Android Java Client
```

## 10. Testing Strategy

Unit tests:

- Probar `AudioContent`, `TextContent`, `LanguageCode`, `AudioFormat`.
- Probar validaciones de `TranscribeAudioUseCase` con `FakeSTTAdapter`.
- Probar validaciones de `SynthesizeSpeechUseCase` con `FakeTTSAdapter`.
- No importar Faster Whisper ni Kokoro en unit tests.

Integration tests:

- FastAPI `TestClient` contra adapters fake.
- Validar status codes, JSON, MIME, headers y error shape.
- Probar multipart real con fixture pequeño `.wav`.
- Probar respuesta binaria de `/voice/synthesize`.

Contract tests:

- `SpeechToTextPort`: cualquier implementación debe retornar `TranscriptionResult` y mapear errores.
- `TextToSpeechPort`: cualquier implementación debe retornar bytes, MIME correcto y errores normalizados.
- Ejecutar los mismos tests contra fake adapter y, opcionalmente, provider real marcado como `pytest.mark.slow`.

Mock/Fake providers:

```python
class FakeSTTAdapter(SpeechToTextPort):
    async def transcribe(self, audio, language=None, beam_size=5):
        return TranscriptionResult(
            text="texto de prueba",
            language="es",
            duration_seconds=1.0,
            segments=[]
        )
```

```python
class FakeTTSAdapter(TextToSpeechPort):
    async def synthesize(self, text, voice, language, audio_format, speed=1.0):
        return SynthesizedSpeech(
            audio_bytes=b"RIFF....WAVE",
            mime_type="audio/wav",
            duration_seconds=1.0,
            format="wav"
        )
```

Cobertura mínima recomendada Sprint 1:

- `85%` en `domain`, `application`, `api`.
- Adapters reales pueden tener cobertura menor si dependen de modelos pesados, pero deben tener contract tests opcionales.

## 11. Performance Strategy

Objetivo: respuesta completa menor a 3 segundos para audios cortos de comandos conversacionales.

Restricciones recomendadas:

- Audio máximo Sprint 1: `10 MB`.
- Duración recomendada Android: `1` a `10` segundos.
- Texto TTS máximo: `1000` caracteres.
- Formato STT recomendado: WAV mono `16 kHz`, PCM 16-bit.
- Formato TTS default: WAV mono.

Optimizaciones STT:

- Cargar Faster Whisper al arrancar la app.
- Usar modelo `base` o `small` para latencia inicial.
- CPU: `compute_type=int8`.
- GPU: `compute_type=float16`.
- Convertir audio a mono/16k antes de transcribir si el proveedor lo requiere.
- Limitar concurrencia STT con semaphore configurable.

Optimizaciones TTS:

- Cargar Kokoro al arrancar.
- Cache opcional LRU para textos repetidos en Sprint 1 P2.
- Mantener salida WAV para evitar costo de encoding MP3.
- Limitar longitud de texto y velocidad.

Concurrencia:

- FastAPI async para I/O.
- Inferencia ML puede ejecutarse en threadpool si bloquea el event loop.
- Configurar `MAX_STT_CONCURRENCY=1..2` y `MAX_TTS_CONCURRENCY=1..2`.
- No permitir requests ilimitados simultáneos.

Memoria:

- No guardar audios en disco por defecto.
- Rechazar requests grandes antes de pasarlos al modelo.
- Liberar buffers temporales al terminar request.
- No cargar múltiples instancias del mismo modelo por worker.

## 12. Android Integration Contract

STT desde Android Java:

- Grabar audio como WAV mono, `16 kHz`, PCM 16-bit.
- Enviar `multipart/form-data`.
- Campo `file`: archivo de audio.
- Campo `language`: `es` o `auto`.
- Timeout recomendado: `10` segundos.
- Mostrar estado de carga mientras espera.

MIME recomendado:

```text
audio/wav
```

Request:

```http
POST /voice/transcribe
Content-Type: multipart/form-data
Accept: application/json
X-Request-Id: UUID
```

TTS desde Android Java:

```http
POST /voice/synthesize
Content-Type: application/json
Accept: audio/wav
X-Request-Id: UUID
```

Body:

```json
{
  "text": "Respuesta del asistente",
  "voice": "default",
  "language": "es",
  "format": "wav",
  "speed": 1.0
}
```

Android debe:

- Reproducir `audio/wav` desde bytes recibidos.
- Manejar `4xx` como error de request.
- Manejar `503` como proveedor no disponible.
- Reintentar solo errores transitorios, no validaciones.
- Enviar `X-Request-Id` para trazabilidad.

## 13. Riesgos y Mitigaciones

Riesgos técnicos:

- Carga lenta de modelos.
  - Mitigación: cargar en startup, readiness endpoint, modelo configurable.
- Dependencias pesadas o incompatibles.
  - Mitigación: aislar adapters, usar contract tests y requirements versionados.
- Event loop bloqueado por inferencia.
  - Mitigación: threadpool/semaphore para llamadas bloqueantes.

Riesgos de integración:

- Android envía formato no compatible.
  - Mitigación: contrato WAV 16k mono y error `415` claro.
- Timeouts en red móvil.
  - Mitigación: límites de duración, timeouts explícitos, payloads pequeños.
- Diferencias entre voces Kokoro disponibles.
  - Mitigación: voz default configurable y endpoint futuro `/voice/voices`.

Riesgos de rendimiento:

- STT supera 3 segundos en CPU.
  - Mitigación: modelo pequeño, int8, límite de duración, GPU opcional.
- TTS lento para textos largos.
  - Mitigación: máximo 1000 caracteres, streaming futuro fuera de Sprint 1.
- Concurrencia excesiva.
  - Mitigación: semaphore y rechazo controlado con `429` si se implementa.

Riesgos de despliegue:

- Imágenes Docker muy grandes.
  - Mitigación: separar dependencias, documentar modelo, usar cache de build.
- Falta de GPU.
  - Mitigación: configuración CPU-first con modelos pequeños.

## 14. Backlog Sprint 1

P0 obligatorio:

| Tarea | Estimación | Dependencias | Entregable |
|---|---:|---|---|
| Crear estructura `voice_module` | 2h | Ninguna | Proyecto base |
| Definir dominio y errores | 3h | Estructura | Value objects y errores |
| Definir puertos STT/TTS | 2h | Dominio | Interfaces abstractas |
| Implementar use cases | 5h | Puertos | `TranscribeAudioUseCase`, `SynthesizeSpeechUseCase` |
| Implementar FastAPI routes | 5h | Use cases | `/voice/transcribe`, `/voice/synthesize` |
| Implementar fake adapters | 2h | Puertos | Tests sin modelos reales |
| Implementar Faster Whisper adapter | 6h | STT port | Adapter real STT |
| Implementar Kokoro adapter | 6h | TTS port | Adapter real TTS |
| Configuración y DI | 4h | Adapters | Container y settings |
| Unit tests use cases | 5h | Fakes | Tests principales |
| Integration tests API con fakes | 5h | API | TestClient |
| Error handling estándar | 3h | API | Error shape estable |

P1 importante:

| Tarea | Estimación | Dependencias | Entregable |
|---|---:|---|---|
| Health/readiness endpoints | 2h | DI | `/health`, `/voice/health` |
| Contract tests de puertos | 4h | Fakes/adapters | Test suite reusable |
| Límites de concurrencia | 3h | Config | Semaphore por provider |
| Logging con request id | 3h | API | Trazabilidad básica |
| Documentación Android contract | 3h | API | README técnico |

P2 deseable:

| Tarea | Estimación | Dependencias | Entregable |
|---|---:|---|---|
| Cache TTS LRU | 3h | TTS adapter | Optimización textos repetidos |
| Endpoint `/voice/voices` | 2h | Kokoro config | Lista de voces |
| Dockerfile | 4h | Dependencias estables | Imagen ejecutable |
| Slow tests con modelos reales | 4h | Modelos instalados | Pruebas marcadas `slow` |

## 15. Definition of Done Sprint 1

Funcional:

- Android puede enviar audio a `/voice/transcribe`.
- La API retorna texto transcrito en JSON.
- Android puede enviar texto a `/voice/synthesize`.
- La API retorna audio reproducible.
- Faster Whisper y Kokoro están integrados mediante adapters.
- Los proveedores pueden reemplazarse sin modificar dominio ni use cases.

Técnico:

- Arquitectura hexagonal respetada.
- Dominio sin dependencias externas.
- Use cases dependen solo de puertos.
- FastAPI solo actúa como adapter de entrada.
- Configuración centralizada por variables de entorno.
- Errores HTTP normalizados.
- Modelos cargados una vez, no por request.

Testing:

- Unit tests para dominio y use cases.
- Integration tests FastAPI con fake adapters.
- Contract tests para STT/TTS ports.
- Cobertura mínima `85%` en dominio, aplicación y API.
- Tests no requieren Faster Whisper ni Kokoro salvo suite `slow`.

Aceptación:

- `/voice/transcribe` responde `200` con texto para un WAV válido.
- `/voice/synthesize` responde `200` con `Content-Type: audio/wav`.
- Requests inválidos retornan `400`, `413` o `415` según corresponda.
- Provider caído retorna `503`.
- Audio corto y texto corto responden idealmente en menos de `3s` en entorno objetivo.
- El README documenta instalación, ejecución, endpoints, contrato Android y ejecución de tests.

## Supuestos Cerrados

- Sprint 1 no incluye agentes, memoria, Qdrant, PostgreSQL, Gemma, tool calling ni ejecución Android.
- No se persistirá audio ni transcripciones.
- WAV mono 16 kHz PCM 16-bit será el formato recomendado Android -> API.
- WAV será el formato default API -> Android.
- La implementación usará fake adapters para pruebas rápidas y adapters reales para ejecución.
- El módulo será diseñado como servicio independiente, preparado para ser consumido luego por un sistema multi-agent sin reestructurar la capa de voz.
