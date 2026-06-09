from typing import Optional
from domain.value_objects import AudioPayload, AudioFormat, Language
from domain.errors import DomainValidationError
from domain.models import Transcription
from ports.stt_port import SpeechToTextPort
from application.dtos import TranscribeAudioInputDTO, TranscribeAudioOutputDTO


ALLOWED_MIME_TYPES = {
    "audio/wav",
    "audio/x-wav",
    "audio/flac",
    "audio/ogg",
    "audio/mpeg",
    "audio/mp3",
}


class TranscribeAudioUseCase:
    def __init__(self, stt_port: SpeechToTextPort):
        self._stt_port = stt_port

    def execute(self, input_dto: TranscribeAudioInputDTO) -> TranscribeAudioOutputDTO:
        if not input_dto.audio_bytes:
            raise DomainValidationError("Audio payload cannot be empty.")

        if input_dto.mime_type not in ALLOWED_MIME_TYPES:
            raise DomainValidationError(f"Unsupported audio mime type: {input_dto.mime_type}")

        if len(input_dto.audio_bytes) > 10_485_760:
            raise DomainValidationError("Audio payload exceeds maximum size of 10 MB.")

        try:
            language = Language(input_dto.language) if input_dto.language else None
            audio_payload = AudioPayload(
                data=input_dto.audio_bytes,
                mime_type=input_dto.mime_type,
                sample_rate=None,
                channels=None,
            )
        except ValueError as exc:
            raise DomainValidationError(str(exc)) from exc

        transcription = self._stt_port.transcribe(
            audio=audio_payload,
            language=language,
            format=input_dto.file_format,
        )

        return TranscribeAudioOutputDTO(
            text=transcription.text,
            language=transcription.language,
            duration_seconds=transcription.duration_seconds,
            confidence=transcription.confidence,
            provider=transcription.provider,
        )
