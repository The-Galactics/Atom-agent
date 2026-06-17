from abc import ABC, abstractmethod

from domain.intent.models import IntentResult


class IntentRecognizerPort(ABC):
    """Contract for turning a natural-language order into a structured action.

    Implementations use function/tool calling: when the user message maps to a
    catalog action the result carries an executable ``Action``; otherwise it
    falls back to a conversational reply (``ActionType.NONE``).
    """

    @abstractmethod
    async def recognize(self, text: str, session_id: str = "default") -> IntentResult:
        """Interpret ``text`` and return the resolved intent."""
        ...
