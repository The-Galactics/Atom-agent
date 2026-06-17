import logging

from langchain_google_genai import ChatGoogleGenerativeAI

from adapters.llm.content import extract_text
from domain.errors import ProviderError
from domain.intent.catalog import openai_tools, spec_for_tool
from domain.intent.models import Action, ActionType, IntentResult
from ports.intent_port import IntentRecognizerPort

logger = logging.getLogger("voice_module")

_SYSTEM_PROMPT = (
    "Eres Atom, un asistente de Android. Cuando el usuario te da una orden que "
    "se corresponde con una de tus herramientas, llama a esa herramienta con los "
    "parámetros adecuados en lugar de responder con texto. Si el mensaje es solo "
    "conversación y no pide una acción concreta del dispositivo, responde con "
    "naturalidad en español sin llamar ninguna herramienta."
)


class GeminiFunctionCallingAdapter(IntentRecognizerPort):
    """Intent recognizer backed by Google Gemini function calling.

    The action catalog is bound to the model as callable tools. A tool call in
    the model response becomes an executable :class:`Action`; a plain text
    response becomes a conversational :class:`IntentResult` (``ActionType.NONE``).
    """

    def __init__(self, api_key: str, model: str = "gemini-1.5-flash"):
        llm = ChatGoogleGenerativeAI(
            model=model,
            google_api_key=api_key,
            temperature=0.0,  # deterministic routing for orders
        )
        # Bind once; the bound model is reused for every recognition call.
        self._llm = llm.bind_tools(openai_tools())

    async def recognize(self, text: str, session_id: str = "default") -> IntentResult:
        messages = [("system", _SYSTEM_PROMPT), ("human", text)]
        try:
            response = await self._llm.ainvoke(messages)
        except Exception as exc:  # noqa: BLE001 - surface provider failures uniformly
            logger.warning("intent_recognize_failed session_id=%s error=%s", session_id, exc)
            raise ProviderError(f"intent recognition failed: {exc}") from exc

        tool_calls = getattr(response, "tool_calls", None) or []
        if not tool_calls:
            # Conversational turn: no action, just the model's reply.
            return IntentResult(
                action=Action(type=ActionType.NONE),
                reply=extract_text(response.content),
                confidence=0.0,
                requires_confirmation=False,
                raw_text=text,
            )

        call = tool_calls[0]
        tool_name = call.get("name", "")
        args = call.get("args", {}) or {}
        spec = spec_for_tool(tool_name)
        if spec is None:
            # Model hallucinated an unknown tool — degrade to conversation.
            logger.warning("intent_unknown_tool session_id=%s tool=%s", session_id, tool_name)
            return IntentResult(
                action=Action(type=ActionType.NONE),
                reply=extract_text(response.content),
                confidence=0.0,
                raw_text=text,
            )

        return IntentResult(
            action=Action(type=spec.type, parameters=dict(args)),
            reply=extract_text(response.content),
            confidence=1.0,
            requires_confirmation=spec.requires_confirmation,
            raw_text=text,
        )
