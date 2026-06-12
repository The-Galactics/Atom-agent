from abc import ABC, abstractmethod
from domain.conversation.models import ChatMessage


class LLMPort(ABC):
    @abstractmethod
    async def chat(
        self,
        messages: list[ChatMessage],
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> ChatMessage:
        """Sends a list of messages to the LLM and returns the assistant's response."""
        pass
