from dataclasses import dataclass


@dataclass
class ChatMessage:
    role: str
    content: str
    timestamp: float | None = None


@dataclass
class Conversation:
    session_id: str
    messages: list[ChatMessage]
