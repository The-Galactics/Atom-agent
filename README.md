# Voice Module

Voice module for Sprint 1 of the intelligent assistant.

## Estructura

- `api/`: FastAPI controllers y schemas.
- `application/`: Casos de uso, DTOs.
- `domain/`: modelos puros y reglas.
- `ports/`: contratos STT/TTS.
- `adapters/`: implementaciones de Faster Whisper y Kokoro.
- `infrastructure/`: configuración y cliente de providers.
- `tests/`: unitarias e integración.

## Uso

1. Instalar dependencias:

```bash
pip install -r requirements.txt
```

2. Ejecutar:

```bash
uvicorn main:app --reload
```

3. Endpoints:

- `POST /voice/transcribe`
- `POST /voice/synthesize`

## Notas

- Las implementaciones de `FasterWhisperAdapter` y `KokoroAdapter` usan adaptadores con carga perezosa de librerías.
- El dominio permanece desacoplado de los providers.
