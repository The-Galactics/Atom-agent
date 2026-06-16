from domain.value_objects import AudioFormat, Language
from domain.errors import DomainValidationError
from ports.tts_port import TextToSpeechPort
from application.dtos import SynthesizeSpeechInputDTO, SynthesizeSpeechOutputDTO


class SynthesizeSpeechUseCase:
    # Validates text input and delegates synthesis to TTS port.
    def __init__(
        self,
        tts_port: TextToSpeechPort,
        max_text_chars: int = 1000,
        default_language: str = "es",
    ):
        self._tts_port = tts_port
        self._max_text_chars = max_text_chars
        self._default_language = default_language

    def execute(self, input_dto: SynthesizeSpeechInputDTO) -> SynthesizeSpeechOutputDTO:
        # Validate text and speed constraints.
        if not input_dto.text or not input_dto.text.strip():
            raise DomainValidationError("Text cannot be empty.")

        normalized_text = input_dto.text.strip()

        if len(normalized_text) > self._max_text_chars:
            raise DomainValidationError(
                f"Text length exceeds {self._max_text_chars} characters."
            )

        if input_dto.speed < 0.75 or input_dto.speed > 1.25:
            raise DomainValidationError("Speech speed must be between 0.75 and 1.25.")

        try:
            # Build validated domain values from DTO values.
            audio_format = AudioFormat.from_string(input_dto.audio_format)
            language = Language(input_dto.language or self._default_language)
        except ValueError as exc:
            raise DomainValidationError(str(exc)) from exc

        synthesis = self._tts_port.synthesize(
            text=normalized_text,
            voice=input_dto.voice,
            format=audio_format,
            language=language.code,
            speed=input_dto.speed,
        )

        # Map domain model into output DTO.
        return SynthesizeSpeechOutputDTO(
            audio_bytes=synthesis.audio_bytes,
            mime_type=synthesis.mime_type,
            format=synthesis.format,
            duration_seconds=synthesis.duration_seconds,
            provider=synthesis.provider,
        )
