from __future__ import annotations
from abc import ABC, abstractmethod
from domain.value_objects import AudioFormat
from domain.models import SynthesisResult


class TextToSpeechPort(ABC):
    @abstractmethod
    def synthesize(
        self,
        text: str,
        voice: str | None = None,
        format: AudioFormat = AudioFormat.WAV,
        language: str | None = None,
        speed: float = 1.0,
    ) -> SynthesisResult:
        raise NotImplementedError
