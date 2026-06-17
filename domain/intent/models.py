from dataclasses import dataclass, field
from enum import Enum


class ActionType(str, Enum):
    """Closed catalog of actions the Android client knows how to execute.

    ``NONE`` is the conversational fallback: the user message did not map to
    an executable order, so the client should just speak/show ``reply``.
    """

    OPEN_APP = "OPEN_APP"
    MAKE_CALL = "MAKE_CALL"
    SEND_MESSAGE = "SEND_MESSAGE"
    SET_ALARM = "SET_ALARM"
    SET_TIMER = "SET_TIMER"
    TOGGLE_SETTING = "TOGGLE_SETTING"
    NONE = "NONE"

    @classmethod
    def from_string(cls, value: str) -> "ActionType":
        try:
            return cls(value.upper())
        except ValueError:
            return cls.NONE


@dataclass
class Action:
    """A resolved, executable action with its filled-in slots."""

    type: ActionType
    parameters: dict = field(default_factory=dict)

    @property
    def is_executable(self) -> bool:
        return self.type is not ActionType.NONE


@dataclass
class IntentResult:
    """Outcome of interpreting a user order.

    Either ``action.is_executable`` is True (the client runs it) or the turn
    was conversational and only ``reply`` is meaningful.
    """

    action: Action
    reply: str
    confidence: float = 0.0
    requires_confirmation: bool = False
    raw_text: str = ""
