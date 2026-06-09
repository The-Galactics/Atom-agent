from __future__ import annotations
import os
import tempfile
from typing import Any
from domain.errors import ProviderError
from domain.value_objects import AudioPayload, Language
from domain.models import Transcription
from ports.stt_port import SpeechToTextPort

try:
    from faster_whisper import WhisperModel
except ImportError:  # pragma: no cover
    WhisperModel = None


class FasterWhisperAdapter(SpeechToTextPort):
    def __init__(self, model_name: str = "small", device: str = "cpu") -> None:
        if WhisperModel is None:
            raise RuntimeError("faster_whisper is not installed. Install optional provider requirements.")
        self._model = WhisperModel(model_name, device=device)
        self._temp_files: list[str] = []

    def transcribe(
        self,
        audio: AudioPayload,
        language: Language | None = None,
        format: str | None = None,
    ) -> Transcription:
        temp_path = audio.save_to_temp_file()
        self._temp_files.append(temp_path)

        try:
            options: dict[str, Any] = {}
            if language:
                options["language"] = language.code
                options["task"] = "transcribe"

            segments, info = self._model.transcribe(temp_path, **options)
            text = " ".join(segment.text.strip() for segment in segments if segment.text)
            confidence = None
            if hasattr(info, "avg_logprob"):
                confidence = float(info.avg_logprob)

            return Transcription(
                text=text,
                language=language.code if language else getattr(info, "language", "unknown"),
                duration_seconds=getattr(info, "duration", None),
                confidence=confidence,
                provider="faster_whisper",
            )
        except Exception as exc:
            raise ProviderError(f"Faster Whisper failed: {exc}") from exc

    def shutdown(self) -> None:
        for temp_path in self._temp_files:
            try:
                os.remove(temp_path)
            except OSError:
                pass
        self._temp_files.clear()
