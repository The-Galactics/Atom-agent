import pytest
from application.use_cases.transcribe_audio import TranscribeAudioUseCase
from application.use_cases.synthesize_speech import SynthesizeSpeechUseCase
from application.use_cases.chat import ChatUseCase
from application.dtos import TranscribeAudioInputDTO, SynthesizeSpeechInputDTO, ChatInputDTO
from tests.fixtures.mocks import FakeSpeechToTextPort, FakeTextToSpeechPort


class FakeHistoryPort:
    def __init__(self):
        self.history = {}

    def get_history(self, session_id: str):
        return self.history.get(session_id, [])

    def add_message(self, session_id: str, message):
        if session_id not in self.history:
            self.history[session_id] = []
        self.history[session_id].append(message)

    def clear(self, session_id: str):
        self.history[session_id] = []


class MockGraph:
    async def ainvoke(self, state):
        from domain.conversation.models import ChatMessage
        assistant_msg = ChatMessage(role="assistant", content="Hola! Soy Atom.")
        state["messages"].append(assistant_msg)
        state["response"] = assistant_msg
        return state


import asyncio

def test_chat_use_case():
    history = FakeHistoryPort()
    graph = MockGraph()
    use_case = ChatUseCase(graph=graph, history_adapter=history)
    
    input_dto = ChatInputDTO(text="Hola", session_id="user_1")
    output = asyncio.run(use_case.execute(input_dto))
    
    assert output.text == "Hola! Soy Atom."
    assert output.session_id == "user_1"
    assert len(history.get_history("user_1")) > 0


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
    output = asyncio.run(use_case.execute(input_dto))

    assert output.audio_bytes == b"FAKEAUDIO"
    assert output.mime_type == "audio/mpeg"
    assert output.provider == "fake_tts"


def test_synthesize_speech_use_case_empty_text():
    port = FakeTextToSpeechPort()
    use_case = SynthesizeSpeechUseCase(tts_port=port)
    with pytest.raises(Exception):
        asyncio.run(use_case.execute(SynthesizeSpeechInputDTO(text="", audio_format="mp3")))
