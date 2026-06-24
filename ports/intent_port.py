from abc import ABC, abstractmethod

from domain.intent.models import IntentResult


class IntentRecognizerPort(ABC):
    """Contract for turning a natural-language order into a structured action.

    Implementations use function/tool calling: when the user message maps to a
    catalog action the result carries an executable ``Action``; otherwise it
    falls back to a conversational reply (``ActionType.NONE``).
    """

    @abstractmethod
    async def recognize(
        self, text: str, session_id: str = "default", screen=None, history=None
    ) -> IntentResult:
        """Interpret ``text`` and return the resolved intent.

        ``screen`` is an optional list of visible screen elements (each carrying
        the ScreenElement fields) so the recognizer can reason over real screen
        structure. ``history`` is an optional ordered list of rendered prior
        action steps for ReAct chaining. ``None`` for either keeps existing
        single-shot callers valid.
        """
        ...
