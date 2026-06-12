from domain.errors import ProviderError
from domain.value_objects import AudioFormat, Language
from domain.voice.models import SynthesisResult
from ports.tts_port import TextToSpeechPort
from infrastructure.provider_clients import KokoroClient


class KokoroAdapter(TextToSpeechPort):
    def __init__(
        self,
        kokoro_client: KokoroClient,
        default_voice: str = "af_heart",
        default_format: AudioFormat | str = AudioFormat.WAV,
    ) -> None:
        self._client = kokoro_client
        self._default_voice = default_voice
        self._default_format = (
            default_format
            if isinstance(default_format, AudioFormat)
            else AudioFormat.from_string(default_format)
        )

    def synthesize(
        self,
        text: str,
        voice: str | None = None,
        format: AudioFormat = AudioFormat.WAV,
        language: str | None = None,
        speed: float = 1.0,
    ) -> SynthesisResult:
        selected_voice = voice or self._default_voice
        selected_format = format or self._default_format
        try:
            audio_bytes = self._client.synthesize(
                text=text,
                voice=selected_voice,
                audio_format=selected_format.value,
                language=language,
                speed=speed,
            )
            return SynthesisResult(
                audio_bytes=audio_bytes,
                mime_type=selected_format.to_mime_type(),
                format=selected_format.value,
                duration_seconds=None,
                provider="kokoro",
            )
        except Exception as exc:
            raise ProviderError(f"Kokoro synthesis failed: {exc}") from exc
