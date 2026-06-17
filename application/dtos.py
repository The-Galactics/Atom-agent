from dataclasses import dataclass


@dataclass
class TranscribeAudioInputDTO:
    # Input payload expected by transcribe use case.
    audio_bytes: bytes
    mime_type: str
    language: str | None = None
    file_format: str | None = None
    beam_size: int = 5


@dataclass
class TranscribeAudioOutputDTO:
    # Output payload produced by transcribe use case.
    text: str
    language: str
    duration_seconds: float | None = None
    confidence: float | None = None
    provider: str = ""


@dataclass
class SynthesizeSpeechInputDTO:
    # Input payload expected by synthesize use case.
    text: str
    voice: str | None = None
    audio_format: str = "wav"
    language: str | None = None
    speed: float = 1.0


@dataclass
class SynthesizeSpeechOutputDTO:
    # Output payload produced by synthesize use case.
    audio_bytes: bytes
    mime_type: str
    format: str
    duration_seconds: float | None = None
    provider: str = ""


@dataclass
class ChatInputDTO:
    text: str
    session_id: str = "default"


@dataclass
class ChatOutputDTO:
    text: str
    session_id: str


@dataclass
class ExecuteCommandInputDTO:
    text: str
    user_id: str = "default"


@dataclass
class ExecuteCommandOutputDTO:
    success: bool
    reply_text: str
    action_type: str
    parameters: dict
    confidence: float = 0.0
    requires_confirmation: bool = False
