from domain.conversation.models import ChatMessage
from ports.history_port import HistoryPort


class InMemoryHistoryAdapter(HistoryPort):
    # In-memory ephemeral history (useful for development/testing).
    def __init__(self):
        self._histories: dict[str, list[ChatMessage]] = {}

    def get_history(self, session_id: str) -> list[ChatMessage]:
        # Return existing session messages or empty list.
        return self._histories.get(session_id, [])

    def add_message(self, session_id: str, message: ChatMessage):
        # Lazily initialize and append a message.
        if session_id not in self._histories:
            self._histories[session_id] = []
        self._histories[session_id].append(message)

    def clear(self, session_id: str):
        # Remove all messages for the given session.
        if session_id in self._histories:
            self._histories[session_id] = []
