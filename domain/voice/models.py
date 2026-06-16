from dataclasses import dataclass


@dataclass
class Transcription:
    # Canonical STT result returned by speech providers.
    text: str
    language: str
    duration_seconds: float | None = None
    confidence: float | None = None
    provider: str = ""


@dataclass
class SynthesisResult:
    # Canonical TTS result returned by speech providers.
    audio_bytes: bytes
    mime_type: str
    format: str
    duration_seconds: float | None = None
    provider: str = ""
