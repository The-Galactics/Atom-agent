from abc import ABC, abstractmethod
from domain.conversation.models import ChatMessage


class LLMPort(ABC):
    # Contract for chat-capable language models.
    @abstractmethod
    async def chat(
        self,
        messages: list[ChatMessage],
        temperature: float = 0.7,
        max_tokens: int = 1024,
        web_search: bool | None = None,
    ) -> ChatMessage:
        """Sends a list of messages to the LLM and returns the assistant's response."""
        pass
