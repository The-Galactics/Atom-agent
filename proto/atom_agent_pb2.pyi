from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Optional as _Optional

DESCRIPTOR: _descriptor.FileDescriptor

class CommandRequest(_message.Message):
    __slots__ = ("user_id", "command")
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    COMMAND_FIELD_NUMBER: _ClassVar[int]
    user_id: str
    command: str
    def __init__(self, user_id: _Optional[str] = ..., command: _Optional[str] = ...) -> None: ...

class CommandResponse(_message.Message):
    __slots__ = ("success", "out_message")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    OUT_MESSAGE_FIELD_NUMBER: _ClassVar[int]
    success: bool
    out_message: str
    def __init__(self, success: _Optional[bool] = ..., out_message: _Optional[str] = ...) -> None: ...

class MessageRequest(_message.Message):
    __slots__ = ("user_id", "chat_id", "message")
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    CHAT_ID_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    user_id: str
    chat_id: str
    message: str
    def __init__(self, user_id: _Optional[str] = ..., chat_id: _Optional[str] = ..., message: _Optional[str] = ...) -> None: ...

class MessageResponse(_message.Message):
    __slots__ = ("script_token", "status", "finished")
    SCRIPT_TOKEN_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    FINISHED_FIELD_NUMBER: _ClassVar[int]
    script_token: str
    status: str
    finished: bool
    def __init__(self, script_token: _Optional[str] = ..., status: _Optional[str] = ..., finished: _Optional[bool] = ...) -> None: ...

class TranscribeRequest(_message.Message):
    __slots__ = ("audio_bytes", "mime_type", "language", "format", "beam_size")
    AUDIO_BYTES_FIELD_NUMBER: _ClassVar[int]
    MIME_TYPE_FIELD_NUMBER: _ClassVar[int]
    LANGUAGE_FIELD_NUMBER: _ClassVar[int]
    FORMAT_FIELD_NUMBER: _ClassVar[int]
    BEAM_SIZE_FIELD_NUMBER: _ClassVar[int]
    audio_bytes: bytes
    mime_type: str
    language: str
    format: str
    beam_size: int
    def __init__(self, audio_bytes: _Optional[bytes] = ..., mime_type: _Optional[str] = ..., language: _Optional[str] = ..., format: _Optional[str] = ..., beam_size: _Optional[int] = ...) -> None: ...

class TranscribeResponse(_message.Message):
    __slots__ = ("text", "language", "duration_seconds", "confidence", "provider")
    TEXT_FIELD_NUMBER: _ClassVar[int]
    LANGUAGE_FIELD_NUMBER: _ClassVar[int]
    DURATION_SECONDS_FIELD_NUMBER: _ClassVar[int]
    CONFIDENCE_FIELD_NUMBER: _ClassVar[int]
    PROVIDER_FIELD_NUMBER: _ClassVar[int]
    text: str
    language: str
    duration_seconds: float
    confidence: float
    provider: str
    def __init__(self, text: _Optional[str] = ..., language: _Optional[str] = ..., duration_seconds: _Optional[float] = ..., confidence: _Optional[float] = ..., provider: _Optional[str] = ...) -> None: ...

class SynthesizeRequest(_message.Message):
    __slots__ = ("text", "voice", "language", "format", "speed")
    TEXT_FIELD_NUMBER: _ClassVar[int]
    VOICE_FIELD_NUMBER: _ClassVar[int]
    LANGUAGE_FIELD_NUMBER: _ClassVar[int]
    FORMAT_FIELD_NUMBER: _ClassVar[int]
    SPEED_FIELD_NUMBER: _ClassVar[int]
    text: str
    voice: str
    language: str
    format: str
    speed: float
    def __init__(self, text: _Optional[str] = ..., voice: _Optional[str] = ..., language: _Optional[str] = ..., format: _Optional[str] = ..., speed: _Optional[float] = ...) -> None: ...

class SynthesizeResponse(_message.Message):
    __slots__ = ("audio_bytes", "mime_type", "format")
    AUDIO_BYTES_FIELD_NUMBER: _ClassVar[int]
    MIME_TYPE_FIELD_NUMBER: _ClassVar[int]
    FORMAT_FIELD_NUMBER: _ClassVar[int]
    audio_bytes: bytes
    mime_type: str
    format: str
    def __init__(self, audio_bytes: _Optional[bytes] = ..., mime_type: _Optional[str] = ..., format: _Optional[str] = ...) -> None: ...
