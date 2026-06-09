from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import tempfile


class AudioFormat(str, Enum):
    MP3 = "mp3"
    WAV = "wav"
    OGG = "ogg"
    FLAC = "flac"

    @classmethod
    def from_string(cls, format_value: str) -> "AudioFormat":
        normalized = format_value.lower().strip()
        try:
            return cls(normalized)
        except ValueError as exc:
            raise ValueError(f"Unsupported audio format: {format_value}") from exc

    @classmethod
    def from_mime_type(cls, mime_type: str) -> "AudioFormat":
        mapping = {
            "audio/mpeg": cls.MP3,
            "audio/mp3": cls.MP3,
            "audio/wav": cls.WAV,
            "audio/x-wav": cls.WAV,
            "audio/ogg": cls.OGG,
            "audio/flac": cls.FLAC,
        }
        try:
            return mapping[mime_type]
        except KeyError as exc:
            raise ValueError(f"Unsupported mime type for audio format: {mime_type}") from exc

    def to_mime_type(self) -> str:
        return {
            AudioFormat.MP3: "audio/mpeg",
            AudioFormat.WAV: "audio/wav",
            AudioFormat.OGG: "audio/ogg",
            AudioFormat.FLAC: "audio/flac",
        }[self]

    def file_extension(self) -> str:
        return self.value


@dataclass(frozen=True)
class Language:
    code: str

    def __post_init__(self) -> None:
        if not self.code or not self.code.strip():
            raise ValueError("Language code cannot be empty.")

        if len(self.code) > 10:
            raise ValueError("Language code is too long.")

        object.__setattr__(self, "code", self.code.strip())


@dataclass
class AudioPayload:
    data: bytes
    mime_type: str
    sample_rate: int | None = None
    channels: int | None = None

    def __post_init__(self) -> None:
        if not self.data:
            raise ValueError("Audio payload cannot be empty.")
        if not self.mime_type:
            raise ValueError("Audio mime type cannot be empty.")

    @property
    def format(self) -> AudioFormat:
        return AudioFormat.from_mime_type(self.mime_type)

    def save_to_temp_file(self) -> str:
        suffix = f".{self.format.file_extension()}"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            temp_file.write(self.data)
            return temp_file.name
