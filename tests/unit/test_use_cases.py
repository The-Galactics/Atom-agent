import pytest
from application.use_cases.transcribe_audio import TranscribeAudioUseCase
from application.use_cases.synthesize_speech import SynthesizeSpeechUseCase
from application.dtos import TranscribeAudioInputDTO, SynthesizeSpeechInputDTO
from tests.fixtures.mocks import FakeSpeechToTextPort, FakeTextToSpeechPort


def test_transcribe_audio_use_case():
    port = FakeSpeechToTextPort()
    use_case = TranscribeAudioUseCase(stt_port=port)
    input_dto = TranscribeAudioInputDTO(
        audio_bytes=b"fake",
        mime_type="audio/wav",
        language="es-ES",
        file_format="wav",
    )
    output = use_case.execute(input_dto)

    assert output.text == "Este es un texto simulado."
    assert output.language == "es-ES"
    assert output.provider == "fake_stt"


def test_transcribe_audio_use_case_empty_audio():
    port = FakeSpeechToTextPort()
    use_case = TranscribeAudioUseCase(stt_port=port)
    with pytest.raises(Exception):
        use_case.execute(TranscribeAudioInputDTO(audio_bytes=b"", mime_type="audio/wav"))


def test_synthesize_speech_use_case():
    port = FakeTextToSpeechPort()
    use_case = SynthesizeSpeechUseCase(tts_port=port)
    input_dto = SynthesizeSpeechInputDTO(
        text="Hola mundo",
        voice="alloy",
        audio_format="mp3",
        language="es-ES",
    )
    output = use_case.execute(input_dto)

    assert output.audio_bytes == b"FAKEAUDIO"
    assert output.mime_type == "audio/mpeg"
    assert output.provider == "fake_tts"


def test_synthesize_speech_use_case_empty_text():
    port = FakeTextToSpeechPort()
    use_case = SynthesizeSpeechUseCase(tts_port=port)
    with pytest.raises(Exception):
        use_case.execute(SynthesizeSpeechInputDTO(text="", audio_format="mp3"))
