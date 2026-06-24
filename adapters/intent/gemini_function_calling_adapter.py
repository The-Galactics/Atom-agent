import logging

from langchain_google_genai import ChatGoogleGenerativeAI

from adapters.llm.content import extract_text
from domain.datetime_context import current_datetime_sentence
from domain.errors import ProviderError
from domain.intent.catalog import openai_tools, spec_for_tool
from domain.intent.models import Action, ActionType, IntentResult
from ports.intent_port import IntentRecognizerPort

logger = logging.getLogger("voice_module")

_SYSTEM_PROMPT = (
    "Eres Atom, un asistente de Android. SÍ puedes ver la pantalla actual: cuando "
    "hay elementos visibles, se te proporcionan en el mensaje como una lista. "
    "Nunca digas que no puedes ver la pantalla. "
    "REGLA OBLIGATORIA: cuando el usuario pida LEER, OÍR o SABER QUÉ HAY en la "
    "pantalla (por ejemplo 'lee la pantalla', 'léeme la pantalla', 'qué hay en la "
    "pantalla', 'qué ves', 'qué pone', 'descríbeme la pantalla'), DEBES llamar a la "
    "herramienta 'read_screen' SIEMPRE; nunca respondas con texto ni leas los "
    "elementos tú mismo desde el contexto, aunque ya veas la lista de elementos. "
    "Cuando el usuario quiera pulsar, abrir o interactuar con un elemento concreto, "
    "usa 'tap_element' con el texto visible exacto del elemento. "
    "Para introducir texto en un campo de búsqueda o editable (por ejemplo escribir "
    "una consulta), LLAMA a 'type_text' con el texto a escribir; usa 'submit: true' "
    "para ejecutar la búsqueda. No intentes teclear pulsando elementos. Pulsa el "
    "campo primero con 'tap_element' solo si todavía no está enfocado. "
    "Para cualquier otra orden que se corresponda con una de tus herramientas, llama "
    "a esa herramienta con los parámetros adecuados en lugar de responder con texto. "
    "Solo si el mensaje es conversación genuina (saludos, charla) y no pide una "
    "acción ni leer la pantalla, responde con naturalidad en español sin llamar "
    "ninguna herramienta."
)

# Cap rendered elements to bound prompt tokens.
_MAX_SCREEN_LINES = 80


def _attr(el, name):
    # Elements may be dicts or objects (proto-derived/namedtuple).
    if isinstance(el, dict):
        return el.get(name)
    return getattr(el, name, None)


def _render_screen(screen) -> str:
    """Render screen elements compactly: ``[index] role "text" (flags)`` per line."""
    lines = []
    for el in screen[:_MAX_SCREEN_LINES]:
        index = _attr(el, "index")
        role = _attr(el, "role") or "?"
        text = _attr(el, "text") or ""
        flags = [
            name
            for name in ("clickable", "focusable", "editable", "scrollable")
            if _attr(el, name)
        ]
        flag_str = f" ({','.join(flags)})" if flags else ""
        lines.append(f'[{index}] {role} "{text}"{flag_str}')
    return "Elementos visibles en la pantalla actual:\n" + "\n".join(lines)


def _render_history(history) -> str:
    """Render the accumulated ReAct action trace for the model's context."""
    trace = "\n".join(str(step) for step in history)
    return (
        "Acciones ya ejecutadas en esta tarea (ReAct):\n"
        f"{trace}\n"
        "Decide la SIGUIENTE acción para avanzar hacia el objetivo. Si el "
        "objetivo ya está cumplido, no llames ninguna herramienta y responde "
        "con una confirmación breve en español."
    )


class GeminiFunctionCallingAdapter(IntentRecognizerPort):
    """Intent recognizer backed by Google Gemini function calling.

    The action catalog is bound to the model as callable tools. A tool call in
    the model response becomes an executable :class:`Action`; a plain text
    response becomes a conversational :class:`IntentResult` (``ActionType.NONE``).
    """

    def __init__(self, api_key: str, model: str = "gemini-3.1-flash-lite",
                timezone: str = "America/Bogota"):
        llm = ChatGoogleGenerativeAI(
            model=model,
            google_api_key=api_key,
            temperature=0.0,  # deterministic routing for orders
        )
        # Bind once; the bound model is reused for every recognition call.
        self._llm = llm.bind_tools(openai_tools())
        self._timezone = timezone

    async def recognize(
        self, text: str, session_id: str = "default", screen=None, history=None
    ) -> IntentResult:
        # Prepend the real current date/time so the model answers date/day/time
        # questions with the present instead of a training-time guess.
        system_prompt = f"{current_datetime_sentence(self._timezone)}\n\n{_SYSTEM_PROMPT}"
        messages = [("system", system_prompt), ("human", text)]
        if history:
            # Feed the accumulated ReAct trace so the model emits the next step.
            messages.append(("human", _render_history(history)))
        if screen:
            # Give the model the real screen structure so it can target elements.
            messages.append(("human", _render_screen(screen)))
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
        args = dict(call.get("args", {}) or {})
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

        # type_text 'submit' defaults to true per the Android contract; fill it
        # when the model omits the optional slot so the wire params are complete.
        if spec.type is ActionType.TYPE_TEXT and "submit" not in args:
            args["submit"] = True

        return IntentResult(
            action=Action(type=spec.type, parameters=args),
            reply=extract_text(response.content),
            confidence=1.0,
            requires_confirmation=spec.requires_confirmation,
            raw_text=text,
        )
