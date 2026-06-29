from dataclasses import dataclass, field


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
    # Structured screen snapshot from the client when accessibility is enabled.
    screen_elements: list = field(default_factory=list)
    # Per-command id scoping the ReAct trace. Falls back to user_id when the
    # client doesn't supply one (back-compat). A new order id => fresh history.
    order_id: str | None = None
    # Action types that require the conversational "ask first" confirmation for
    # this user. None => the default outward-facing set (DEFAULT_CONFIRM_ACTIONS:
    # MAKE_CALL, SEND_MESSAGE); an empty set => confirm nothing (full autonomy).
    confirm_actions: frozenset[str] | None = None


@dataclass
class ExecuteCommandOutputDTO:
    success: bool
    reply_text: str
    action_type: str
    parameters: dict
    confidence: float = 0.0
    requires_confirmation: bool = False
    # True when the ReAct task is finished; the client stops looping.
    task_complete: bool = False
    # True when the backend holds a sensitive action awaiting spoken sí/no; action_type is NONE
    # and out_message carries the question. Client resends the reply with the same order_id.
    awaiting_confirmation: bool = False
    # Current ReAct step index for this session (telemetry/debug).
    step: int = 0
