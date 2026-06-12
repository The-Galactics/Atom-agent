from abc import ABC, abstractmethod
from domain.conversation.models import ChatMessage


class HistoryPort(ABC):
    @abstractmethod
    def get_history(self, session_id: str) -> list[ChatMessage]:
        """Retrieves the conversation history for a session."""
        pass

    @abstractmethod
    def add_message(self, session_id: str, message: ChatMessage) -> None:
        """Adds a message to the session history."""
        pass

    @abstractmethod
    def clear(self, session_id: str) -> None:
        """Clears the history for a session."""
        pass
