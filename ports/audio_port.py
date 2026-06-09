from __future__ import annotations
from abc import ABC, abstractmethod
from domain.value_objects import AudioPayload


class AudioStoragePort(ABC):
    @abstractmethod
    def save(self, key: str, audio: AudioPayload) -> str:
        raise NotImplementedError

    @abstractmethod
    def load(self, key: str) -> AudioPayload:
        raise NotImplementedError
