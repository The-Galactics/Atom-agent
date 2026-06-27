import asyncio
import re
from collections import OrderedDict

from application.agents.session_store import SessionStore
from application.dtos import ExecuteCommandInputDTO, ExecuteCommandOutputDTO
from domain.intent.models import Action, ActionType, IntentResult
from ports.intent_port import IntentRecognizerPort

# Prior steps that must match the current action before the loop is "stuck".
# 2 => 3 identical actions in a row; tolerates one transient repeat.
STUCK_REPEAT_THRESHOLD = 2

# Actions always held for spoken sí/no confirmation before executing.
# Ownership moved here from the Android client so one backend handshake drives the flow.
ALWAYS_CONFIRM: frozenset[ActionType] = frozenset(
    {ActionType.MAKE_CALL, ActionType.SEND_MESSAGE}
)

# Whole-token affirmatives (es/en), accent-aware. Matched against the FIRST
# spoken token only so "silencio"/"siempre"/"sin" don't read as "sí".
_AFFIRMATIVE_TOKENS: frozenset[str] = frozenset(
    {
        "sí", "si", "claro", "dale", "vale", "ok", "okay", "oka", "correcto",
        "confirmo", "confirma", "hazlo", "adelante", "envia", "envía", "manda",
        "llama", "yes", "yeah", "yep", "sure",
    }
)

# Upper bound on outstanding held actions, so abandoned/preflight holds (each
# keyed by a throwaway order id) can't grow without bound. LRU-evicted.
_MAX_PENDING = 1000


def _is_affirmative(text: str) -> bool:
    """True when ``text`` reads as an affirmative spoken reply (sí/claro/ok…)."""
    if not text:
        return False
    first = text.strip().lower().split()
    if not first:
        return False
    token = re.sub(r"[^a-záéíóúñ]", "", first[0])
    return token in _AFFIRMATIVE_TOKENS


def _signature(action: Action) -> str:
    """Stable identity of an action (type + slots) for de-duping confirmations."""
    return f"{action.type.value} {action.parameters}"


def _confirmation_question(action: Action) -> str:
    """The out-loud question to ask before running a sensitive action."""
    params = action.parameters
    if action.type is ActionType.SEND_MESSAGE:
        recipient = params.get("recipient")
        return (
            f"Voy a enviar un mensaje a {recipient}. ¿Lo confirmo?"
            if recipient
            else "¿Confirmo el envío del mensaje?"
        )
    if action.type is ActionType.MAKE_CALL:
        target = params.get("target")
        return (
            f"Voy a llamar a {target}. ¿Lo confirmo?"
            if target
            else "¿Confirmo la llamada?"
        )
    return "¿Confirmo la acción?"


class ExecuteCommandUseCase:
    """Step-wise ReAct orchestrator for the order/intent path.

    Each ``execute`` call is exactly one ReAct step: load the session's prior
    action trace, ask the recognizer for the next action given the live screen
    and that history, then record it. The loop is distributed across gRPC calls
    (the client re-captures the screen and calls again with the same
    ``session_id``); the backend emits one action per call plus a
    ``task_complete`` signal. Recognition lives behind
    :class:`IntentRecognizerPort`, so the LLM is fully mockable in tests.

    Intrinsically sensitive actions (calling, messaging) are not emitted on
    first sight: the backend HOLDS the action and returns a NONE turn with
    ``awaiting_confirmation`` and the question in ``reply_text``. The client
    speaks it, captures the spoken sí/no, and resends that as the next command
    with the same ``order_id``; an affirmative releases the held action, anything
    else cancels the task.
    """

    def __init__(
        self,
        intent_recognizer: IntentRecognizerPort,
        session_store: SessionStore | None = None,
        max_steps: int = 20,
    ):
        self.intent_recognizer = intent_recognizer
        self.session_store = session_store or SessionStore(max_steps_per_session=max_steps)
        self.max_steps = max_steps
        # One lock per trace key serializes get->recognize->append so concurrent
        # calls for the same order can't both read identical history (TOCTOU).
        self._locks: dict[str, asyncio.Lock] = {}
        # Held sensitive action awaiting a spoken sí/no, keyed by session id.
        self._pending: OrderedDict[str, Action] = OrderedDict()
        # Signatures already confirmed in a session, so a re-recognized identical
        # action isn't held (and re-asked) a second time within the same task.
        self._confirmed: dict[str, set[str]] = {}

    def _lock_for(self, key: str) -> asyncio.Lock:
        lock = self._locks.get(key)
        if lock is None:
            lock = asyncio.Lock()
            self._locks[key] = lock
        return lock

    def _release_lock(self, key: str, lock: asyncio.Lock) -> None:
        """Evict *key* from the registry if no coroutine holds or awaits the lock.

        Called after session reset so the registry stays bounded.
        ``_waiters`` is a private asyncio.Lock attribute; accessed via getattr to
        isolate the coupling in one place.
        """
        pending = bool(getattr(lock, "_waiters", None))
        if not lock.locked() and not pending:
            self._locks.pop(key, None)

    def _reset_session(self, session_id: str) -> None:
        """Drop all per-session state (trace, held action, confirmed signatures)."""
        self.session_store.reset(session_id)
        self._pending.pop(session_id, None)
        self._confirmed.pop(session_id, None)

    def _hold(self, session_id: str, action: Action) -> None:
        """Record a held action awaiting confirmation, LRU-bounded."""
        self._pending.pop(session_id, None)
        self._pending[session_id] = action
        while len(self._pending) > _MAX_PENDING:
            self._pending.popitem(last=False)

    def _needs_confirmation(self, action: Action, session_id: str) -> bool:
        return (
            action.is_executable
            and action.type in ALWAYS_CONFIRM
            and _signature(action) not in self._confirmed.get(session_id, set())
        )

    async def execute(self, input_dto: ExecuteCommandInputDTO) -> ExecuteCommandOutputDTO:
        # Scope the trace per order, not per user: an abandoned multi-step task
        # no longer leaks its partial trace into the user's next command.
        session_id = input_dto.order_id or input_dto.user_id
        lock = self._lock_for(session_id)
        async with lock:
            result = await self._execute_locked(input_dto, session_id)
        if result.task_complete:
            self._release_lock(session_id, lock)
        return result

    async def _recognize(
        self, input_dto: ExecuteCommandInputDTO, session_id: str, history: list[str]
    ) -> IntentResult:
        # Back-compat: only pass history when present so single-shot callers
        # and recognizers without a history param stay valid.
        if history:
            return await self.intent_recognizer.recognize(
                input_dto.text,
                session_id=session_id,
                screen=input_dto.screen_elements,
                history=history,
            )
        return await self.intent_recognizer.recognize(
            input_dto.text,
            session_id=session_id,
            screen=input_dto.screen_elements,
        )

    async def _execute_locked(
        self, input_dto: ExecuteCommandInputDTO, session_id: str
    ) -> ExecuteCommandOutputDTO:
        history = self.session_store.get(session_id)
        step = len(history) + 1

        # Boundary: cap reached before reasoning -> force graceful completion.
        if len(history) >= self.max_steps:
            self._reset_session(session_id)
            return ExecuteCommandOutputDTO(
                success=True,
                reply_text="He alcanzado el límite de pasos para esta tarea.",
                action_type=ActionType.NONE.value,
                parameters={},
                confidence=0.0,
                requires_confirmation=False,
                task_complete=True,
                awaiting_confirmation=False,
                step=len(history),
            )

        # If a sensitive action is held, this turn is the spoken sí/no reply.
        held = self._pending.pop(session_id, None)
        if held is not None:
            if _is_affirmative(input_dto.text):
                # Confirmed: remember it so a re-recognized identical action is
                # not held again, then fall through to emit it as this step.
                self._confirmed.setdefault(session_id, set()).add(_signature(held))
                result = IntentResult(
                    action=held, reply="", confidence=1.0, requires_confirmation=False
                )
            else:
                # Declined (or unclear): cancel the task, fail-closed.
                self._reset_session(session_id)
                return ExecuteCommandOutputDTO(
                    success=True,
                    reply_text="De acuerdo, lo cancelo.",
                    action_type=ActionType.NONE.value,
                    parameters={},
                    confidence=0.0,
                    requires_confirmation=False,
                    task_complete=True,
                    awaiting_confirmation=False,
                    step=len(history),
                )
        else:
            result = await self._recognize(input_dto, session_id, history)
            # Hold an intrinsically sensitive action and ask out loud instead of
            # emitting it. The client speaks reply_text and resends the sí/no.
            if self._needs_confirmation(result.action, session_id):
                self._hold(session_id, result.action)
                return ExecuteCommandOutputDTO(
                    success=True,
                    reply_text=_confirmation_question(result.action),
                    action_type=ActionType.NONE.value,
                    parameters={},
                    confidence=result.confidence,
                    requires_confirmation=True,
                    task_complete=False,
                    awaiting_confirmation=True,
                    step=step,
                )

        # Conversational turn (no device action): the recognizer's reply is
        # returned as-is and the action is NONE. The client re-routes these to
        # the StreamChat RPC, which runs the grounded chat path (live web info +
        # memory); answering conversationally here too would only duplicate it.
        reply = result.reply
        if not reply and result.action.is_executable:
            # Default spoken confirmation for a bare tool call with no text.
            reply = "De acuerdo."

        action_type = result.action.type
        rendered = f"Step {step}: {action_type.value} {result.action.parameters}"

        # Completion: the model signals done with a conversational turn after at
        # least one prior action.
        task_complete = not result.action.is_executable and len(history) >= 1

        # Anti-repeat: declare "stuck" only when the current action and the last
        # STUCK_REPEAT_THRESHOLD steps are all identical (3 in a row).
        if result.action.is_executable and len(history) >= STUCK_REPEAT_THRESHOLD:
            current = f"{action_type.value} {result.action.parameters}"
            recent = history[-STUCK_REPEAT_THRESHOLD:]
            if all(step_entry.split(": ", 1)[-1] == current for step_entry in recent):
                task_complete = True

        if not task_complete and result.action.is_executable:
            self.session_store.append(session_id, rendered)
            # Forced completion when this action hits the cap.
            if step >= self.max_steps:
                task_complete = True

        if task_complete:
            self._reset_session(session_id)

        return ExecuteCommandOutputDTO(
            success=action_type is not ActionType.NONE or bool(reply),
            reply_text=reply,
            action_type=action_type.value,
            parameters=result.action.parameters,
            confidence=result.confidence,
            requires_confirmation=result.requires_confirmation,
            task_complete=task_complete,
            awaiting_confirmation=False,
            step=step,
        )
