"""Natural-language confirmation prompts for the conversational confirm flow.

When the agent proposes a sensitive action it asks the user out loud before
executing. Phrasing lives here (domain, deterministic, testable) rather than in
the LLM adapter, co-located with the action catalog it describes. Spanish by
default, matching the assistant persona.
"""

from __future__ import annotations

from domain.intent.models import ActionType


def confirmation_prompt(action_type: ActionType, parameters: dict | None = None) -> str:
    """Return the question to ask the user before running ``action_type``."""
    params = parameters or {}

    if action_type is ActionType.MAKE_CALL:
        target = params.get("target")
        return f"¿Confirmas que llame a {target}?" if target else "¿Confirmas que haga la llamada?"

    if action_type is ActionType.SEND_MESSAGE:
        recipient = params.get("recipient")
        return (
            f"¿Confirmas que envíe el mensaje a {recipient}?"
            if recipient
            else "¿Confirmas que envíe el mensaje?"
        )

    if action_type is ActionType.TAP_ELEMENT:
        text = params.get("text")
        return f"¿Confirmas que pulse '{text}'?" if text else "¿Confirmas que pulse el elemento?"

    return "¿Confirmas esta acción?"
