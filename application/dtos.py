from dataclasses import dataclass


@dataclass
class TranscribeAudioInputDTO:
    audio_bytes: bytes
    mime_type: str
    language: str | None = None
    file_format: str | None = None
    beam_size: int = 5


@dataclass
class TranscribeAudioOutputDTO:
    text: str
    language: str
    duration_seconds: float | None = None
    confidence: float | None = None
    provider: str = ""


@dataclass
class SynthesizeSpeechInputDTO:
    text: str
    voice: str | None = None
    audio_format: str = "wav"
    language: str | None = None
    speed: float = 1.0


@dataclass
class SynthesizeSpeechOutputDTO:
    audio_bytes: bytes
    mime_type: str
    format: str
    duration_seconds: float | None = None
    provider: str = ""
