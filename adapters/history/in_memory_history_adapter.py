from domain.conversation.models import ChatMessage
from ports.history_port import HistoryPort


class InMemoryHistoryAdapter(HistoryPort):
    # In-memory ephemeral history (useful for development/testing).
    def __init__(self, max_messages_per_session: int = 50):
        self._histories: dict[str, list[ChatMessage]] = {}
        # Bound per-session growth so long-lived sessions don't leak memory.
        # <= 0 disables the cap (unbounded).
        self._max_messages_per_session = max_messages_per_session

    def get_history(self, session_id: str) -> list[ChatMessage]:
        # Return existing session messages or empty list.
        return self._histories.get(session_id, [])

    def add_message(self, session_id: str, message: ChatMessage):
        # Lazily initialize and append a message.
        if session_id not in self._histories:
            self._histories[session_id] = []
        history = self._histories[session_id]
        history.append(message)
        # Drop oldest messages once over the cap.
        if self._max_messages_per_session > 0 and len(history) > self._max_messages_per_session:
            del history[: len(history) - self._max_messages_per_session]

    def clear(self, session_id: str):
        # Remove all messages for the given session.
        if session_id in self._histories:
            self._histories[session_id] = []
