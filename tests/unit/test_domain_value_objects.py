import pytest
from domain.value_objects import AudioFormat, AudioPayload, Language


def test_audio_format_from_mime_type():
    assert AudioFormat.from_mime_type("audio/mp3") == AudioFormat.MP3
    assert AudioFormat.from_mime_type("audio/wav") == AudioFormat.WAV


def test_language_validation():
    language = Language("es-ES")
    assert language.code == "es-ES"

    with pytest.raises(ValueError):
        Language("")


def test_audio_payload_save_to_temp_file(tmp_path):
    payload = AudioPayload(data=b"abc", mime_type="audio/wav")
    temp_path = payload.save_to_temp_file()
    assert temp_path.endswith(".wav")
    with open(temp_path, "rb") as file:
        assert file.read() == b"abc"
