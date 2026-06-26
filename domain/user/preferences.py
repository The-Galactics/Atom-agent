"""Per-user confirmation preferences.

Which action TYPES require the conversational "ask first" step is a per-user
setting persisted in ``User.settings`` (Mongo). The default is derived from the
action catalog (every spec flagged ``requires_confirmation``), so adding a new
sensitive action stays a one-line edit in ``catalog.py``.
"""

from __future__ import annotations

from domain.intent.models import ActionType

# Default actions that get a spoken confirmation: the outward-facing, hard-to-undo
# ones. TAP_ELEMENT is deliberately EXCLUDED here — it's the workhorse of
# autonomous on-screen navigation, so blanket-confirming every tap would make
# the ReAct loop unusable; the Android client already gates *destructive* taps
# by keyword (DestructiveActionPolicy). Users can widen/narrow this set.
DEFAULT_CONFIRM_ACTIONS: frozenset[str] = frozenset(
    {ActionType.MAKE_CALL.value, ActionType.SEND_MESSAGE.value}
)

_VALID_ACTIONS = frozenset(member.value for member in ActionType)


def confirm_actions_from_settings(settings: dict | None) -> frozenset[str]:
    """Resolve the set of action types that require confirmation for a user.

    Reads ``settings["confirmation"]["require_for"]`` (a list of ActionType
    names). Unknown/invalid entries are ignored. When the key is absent the
    catalog default applies; an explicit empty list means "confirm nothing".
    """
    if not settings:
        return DEFAULT_CONFIRM_ACTIONS

    confirmation = settings.get("confirmation")
    if not isinstance(confirmation, dict) or "require_for" not in confirmation:
        return DEFAULT_CONFIRM_ACTIONS

    require_for = confirmation.get("require_for")
    if not isinstance(require_for, (list, tuple, set)):
        return DEFAULT_CONFIRM_ACTIONS

    return frozenset(
        str(value).upper()
        for value in require_for
        if str(value).upper() in _VALID_ACTIONS
    )
