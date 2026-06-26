import pytest
from pydantic import ValidationError

from api.schemas import ChatRequest, MAX_CHAT_TEXT_CHARS


def test_chat_request_accepts_normal_text():
    req = ChatRequest(text="hola atom")
    assert req.text == "hola atom"
    assert req.session_id == "default"


def test_chat_request_rejects_empty_text():
    with pytest.raises(ValidationError):
        ChatRequest(text="")


def test_chat_request_rejects_overlong_text():
    with pytest.raises(ValidationError):
        ChatRequest(text="x" * (MAX_CHAT_TEXT_CHARS + 1))
