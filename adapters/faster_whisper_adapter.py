from __future__ import annotations
import os
import threading
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
    def __init__(
        self,
        model_name: str = "small",
        device: str = "cpu",
        compute_type: str = "int8",
        max_concurrency: int = 1,
    ) -> None:
        if WhisperModel is None:
            raise RuntimeError("faster_whisper is not installed. Install optional provider requirements.")
        self._model = WhisperModel(model_name, device=device, compute_type=compute_type)
        self._semaphore = threading.Semaphore(max_concurrency)

    def transcribe(
        self,
        audio: AudioPayload,
        language: Language | None = None,
        format: str | None = None,
        beam_size: int = 5,
    ) -> Transcription:
        temp_path = audio.save_to_temp_file()

        try:
            options: dict[str, Any] = {}
            if language and language.code.lower() != "auto":
                options["language"] = language.code
                options["task"] = "transcribe"
            options["beam_size"] = beam_size

            with self._semaphore:
                segments, info = self._model.transcribe(temp_path, **options)
                materialized_segments = list(segments)

            text = " ".join(segment.text.strip() for segment in materialized_segments if segment.text)
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
        finally:
            try:
                os.remove(temp_path)
            except OSError:
                pass

    def shutdown(self) -> None:
        return None
