from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class ScreenElement(_message.Message):
    __slots__ = ("text", "role", "clickable", "focusable", "editable", "scrollable", "index")
    TEXT_FIELD_NUMBER: _ClassVar[int]
    ROLE_FIELD_NUMBER: _ClassVar[int]
    CLICKABLE_FIELD_NUMBER: _ClassVar[int]
    FOCUSABLE_FIELD_NUMBER: _ClassVar[int]
    EDITABLE_FIELD_NUMBER: _ClassVar[int]
    SCROLLABLE_FIELD_NUMBER: _ClassVar[int]
    INDEX_FIELD_NUMBER: _ClassVar[int]
    text: str
    role: str
    clickable: bool
    focusable: bool
    editable: bool
    scrollable: bool
    index: int
    def __init__(self, text: _Optional[str] = ..., role: _Optional[str] = ..., clickable: _Optional[bool] = ..., focusable: _Optional[bool] = ..., editable: _Optional[bool] = ..., scrollable: _Optional[bool] = ..., index: _Optional[int] = ...) -> None: ...

class CommandRequest(_message.Message):
    __slots__ = ("user_id", "command", "screen_elements")
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    COMMAND_FIELD_NUMBER: _ClassVar[int]
    SCREEN_ELEMENTS_FIELD_NUMBER: _ClassVar[int]
    user_id: str
    command: str
    screen_elements: _containers.RepeatedCompositeFieldContainer[ScreenElement]
    def __init__(self, user_id: _Optional[str] = ..., command: _Optional[str] = ..., screen_elements: _Optional[_Iterable[_Union[ScreenElement, _Mapping]]] = ...) -> None: ...

class CommandResponse(_message.Message):
    __slots__ = ("success", "out_message", "action_type", "parameters_json", "confidence", "requires_confirmation")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    OUT_MESSAGE_FIELD_NUMBER: _ClassVar[int]
    ACTION_TYPE_FIELD_NUMBER: _ClassVar[int]
    PARAMETERS_JSON_FIELD_NUMBER: _ClassVar[int]
    CONFIDENCE_FIELD_NUMBER: _ClassVar[int]
    REQUIRES_CONFIRMATION_FIELD_NUMBER: _ClassVar[int]
    success: bool
    out_message: str
    action_type: str
    parameters_json: str
    confidence: float
    requires_confirmation: bool
    def __init__(self, success: _Optional[bool] = ..., out_message: _Optional[str] = ..., action_type: _Optional[str] = ..., parameters_json: _Optional[str] = ..., confidence: _Optional[float] = ..., requires_confirmation: _Optional[bool] = ...) -> None: ...

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
