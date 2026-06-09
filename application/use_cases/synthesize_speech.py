from domain.value_objects import AudioFormat, Language
from domain.errors import DomainValidationError
from ports.tts_port import TextToSpeechPort
from application.dtos import SynthesizeSpeechInputDTO, SynthesizeSpeechOutputDTO


class SynthesizeSpeechUseCase:
    def __init__(self, tts_port: TextToSpeechPort):
        self._tts_port = tts_port

    def execute(self, input_dto: SynthesizeSpeechInputDTO) -> SynthesizeSpeechOutputDTO:
        if not input_dto.text or not input_dto.text.strip():
            raise DomainValidationError("Text cannot be empty.")

        if len(input_dto.text) > 5000:
            raise DomainValidationError("Text length exceeds 5000 characters.")

        try:
            audio_format = AudioFormat.from_string(input_dto.audio_format)
            language = Language(input_dto.language) if input_dto.language else None
        except ValueError as exc:
            raise DomainValidationError(str(exc)) from exc

        synthesis = self._tts_port.synthesize(
            text=input_dto.text,
            voice=input_dto.voice,
            format=audio_format,
        )

        return SynthesizeSpeechOutputDTO(
            audio_bytes=synthesis.audio_bytes,
            mime_type=synthesis.mime_type,
            format=synthesis.format,
            duration_seconds=synthesis.duration_seconds,
            provider=synthesis.provider,
        )
