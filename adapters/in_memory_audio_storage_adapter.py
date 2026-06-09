from __future__ import annotations

from domain.errors import DomainValidationError
from domain.value_objects import AudioPayload
from ports.audio_port import AudioStoragePort


class InMemoryAudioStorageAdapter(AudioStoragePort):
    def __init__(self) -> None:
        self._items: dict[str, AudioPayload] = {}

    def save(self, key: str, audio: AudioPayload) -> str:
        if not key or not key.strip():
            raise DomainValidationError("Audio storage key cannot be empty.")
        self._items[key] = audio
        return key

    def load(self, key: str) -> AudioPayload:
        try:
            return self._items[key]
        except KeyError as exc:
            raise DomainValidationError(f"Audio storage key not found: {key}") from exc
