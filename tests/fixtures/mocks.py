from domain.voice.models import Transcription, SynthesisResult
from domain.value_objects import AudioFormat, AudioPayload, Language
from ports.stt_port import SpeechToTextPort
from ports.tts_port import TextToSpeechPort


class FakeSpeechToTextPort(SpeechToTextPort):
    def transcribe(
        self,
        audio: AudioPayload,
        language: Language | None = None,
        format: str | None = None,
        beam_size: int = 5,
    ) -> Transcription:
        return Transcription(
            text="Este es un texto simulado.",
            language=language.code if language else "es-ES",
            duration_seconds=2.1,
            confidence=0.96,
            provider="fake_stt",
        )


class FakeTextToSpeechPort(TextToSpeechPort):
    def synthesize(
        self,
        text: str,
        voice: str | None = None,
        format: AudioFormat = AudioFormat.WAV,
        language: str | None = None,
        speed: float = 1.0,
    ) -> SynthesisResult:
        return SynthesisResult(
            audio_bytes=b"FAKEAUDIO",
            mime_type=format.to_mime_type(),
            format=format.value,
            duration_seconds=1.8,
            provider="fake_tts",
        )
