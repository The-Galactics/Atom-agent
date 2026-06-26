import logging

from langchain_google_genai import ChatGoogleGenerativeAI

from adapters.llm.content import extract_text
from application.agents.prompts.intent_prompt import INTENT_SYSTEM_PROMPT
from domain.datetime_context import current_datetime_sentence
from domain.errors import ProviderError
from domain.intent.catalog import openai_tools, spec_for_tool, validate_and_coerce_args
from domain.intent.models import Action, ActionType, IntentResult
from ports.intent_port import IntentRecognizerPort

logger = logging.getLogger("voice_module")

# Back-compat alias: existing imports of _SYSTEM_PROMPT keep working.
_SYSTEM_PROMPT = INTENT_SYSTEM_PROMPT

# Cap rendered elements to bound prompt tokens.
_MAX_SCREEN_LINES = 80

# Text markers identifying decorative profile-photo/avatar elements (unaccented;
# the Spanish strings of interest carry no accents, so casefold matching suffices).
_AVATAR_MARKERS = (
    "foto de perfil", "foto del perfil", "imagen de perfil",
    "avatar", "profile picture", "profile photo",
)


def _is_avatar_element(el) -> bool:
    """True when an element's text names a decorative profile photo/avatar."""
    text = (_attr(el, "text") or "").casefold()
    return any(marker in text for marker in _AVATAR_MARKERS)


def _sanitize_screen(screen) -> list:
    """Drop decorative avatar/profile-photo elements, preserving order and the
    rest of the elements untouched, so the model never targets a profile photo."""
    return [el for el in screen if not _is_avatar_element(el)]


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

    def __init__(self, api_key: str, model: str = "models/gemini-3.1-flash-lite",
                timezone: str = "America/Bogota", system_prompt: str | None = None):
        llm = ChatGoogleGenerativeAI(
            model=model,
            google_api_key=api_key,
            temperature=0.0,  # deterministic routing for orders
        )
        # Bind once; the bound model is reused for every recognition call.
        self._llm = llm.bind_tools(openai_tools())
        self._timezone = timezone
        self._system_prompt = system_prompt or INTENT_SYSTEM_PROMPT

    async def recognize(
        self, text: str, session_id: str = "default", screen=None, history=None
    ) -> IntentResult:
        # Prepend the real current date/time so the model answers date/day/time
        # questions with the present instead of a training-time guess.
        system_prompt = f"{current_datetime_sentence(self._timezone)}\n\n{self._system_prompt}"
        messages = [("system", system_prompt), ("human", text)]
        if history:
            # Feed the accumulated ReAct trace so the model emits the next step.
            messages.append(("human", _render_history(history)))
        if screen:
            # Give the model the real screen structure so it can target elements,
            # minus decorative avatars it would otherwise loop on tapping.
            cleaned = _sanitize_screen(screen)
            if cleaned:
                messages.append(("human", _render_screen(cleaned)))
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

        # The tool layer is untrusted: validate/coerce args against the spec
        # before building the action. On a hard error (missing required slot,
        # enum/type violation) degrade to a conversational turn rather than
        # emitting a malformed action to the client.
        coerced, errors = validate_and_coerce_args(spec, args)
        if errors:
            logger.warning(
                "intent_arg_validation_failed session_id=%s tool=%s errors=%s",
                session_id, tool_name, errors,
            )
            return IntentResult(
                action=Action(type=ActionType.NONE),
                reply="No pude completar esa acción, ¿puedes reformularla?",
                confidence=0.0,
                raw_text=text,
            )

        return IntentResult(
            action=Action(type=spec.type, parameters=coerced),
            reply=extract_text(response.content),
            confidence=1.0,
            requires_confirmation=spec.requires_confirmation,
            raw_text=text,
        )
