import asyncio

from domain.errors import ProviderError
from domain.value_objects import AudioFormat, Language
from domain.voice.models import SynthesisResult
from ports.tts_port import TextToSpeechPort
from infrastructure.provider_clients import KokoroClient


class KokoroAdapter(TextToSpeechPort):
    # Text-to-speech adapter backed by Kokoro HTTP API.
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

    async def synthesize(
        self,
        text: str,
        voice: str | None = None,
        format: AudioFormat = AudioFormat.WAV,
        language: str | None = None,
        speed: float = 1.0,
    ) -> SynthesisResult:
        # Apply defaults and delegate synthesis to provider client.
        selected_voice = voice or self._default_voice
        selected_format = format or self._default_format
        try:
            # KokoroClient uses a blocking HTTP client (requests). Run it in a
            # thread so the synchronous I/O + retry backoff does not block the
            # event loop serving other requests.
            loop = asyncio.get_event_loop()
            audio_bytes = await loop.run_in_executor(
                None,
                lambda: self._client.synthesize(
                    text=text,
                    voice=selected_voice,
                    audio_format=selected_format.value,
                    language=language,
                    speed=speed,
                ),
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
