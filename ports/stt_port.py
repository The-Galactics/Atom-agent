from __future__ import annotations
from abc import ABC, abstractmethod
from domain.value_objects import AudioPayload, Language
from domain.models import Transcription


class SpeechToTextPort(ABC):
    @abstractmethod
    def transcribe(
        self,
        audio: AudioPayload,
        language: Language | None = None,
        format: str | None = None,
    ) -> Transcription:
        raise NotImplementedError
