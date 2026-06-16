from dataclasses import dataclass


@dataclass
class ChatMessage:
    # Single chat message exchanged in a session.
    role: str
    content: str
    timestamp: float | None = None


@dataclass
class Conversation:
    # In-memory conversation aggregate by session id.
    session_id: str
    messages: list[ChatMessage]
