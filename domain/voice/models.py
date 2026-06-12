from dataclasses import dataclass


@dataclass
class Transcription:
    text: str
    language: str
    duration_seconds: float | None = None
    confidence: float | None = None
    provider: str = ""


@dataclass
class SynthesisResult:
    audio_bytes: bytes
    mime_type: str
    format: str
    duration_seconds: float | None = None
    provider: str = ""
