import asyncio
import logging

from application.agents.session_store import SessionStore
from application.dtos import ChatInputDTO, ExecuteCommandInputDTO, ExecuteCommandOutputDTO

logger = logging.getLogger(__name__)
from domain.intent.affirmation import classify_affirmation
from domain.intent.confirmation import confirmation_prompt
from domain.intent.models import ActionType
from domain.user.preferences import DEFAULT_CONFIRM_ACTIONS
from ports.intent_port import IntentRecognizerPort

# Prior steps that must match the current action before the loop is "stuck".
# 2 => 3 identical actions in a row; tolerates one transient repeat.
STUCK_REPEAT_THRESHOLD = 2

# How many times the agent re-asks an unclear confirmation before giving up.
MAX_CONFIRM_REASKS = 2


class ExecuteCommandUseCase:
    """Step-wise ReAct orchestrator for the order/intent path.

    Each ``execute`` call is exactly one ReAct step: load the session's prior
    action trace, ask the recognizer for the next action given the live screen
    and that history, then record it. The loop is distributed across gRPC calls
    (the client re-captures the screen and calls again with the same
    ``session_id``); the backend emits one action per call plus a
    ``task_complete`` signal. Recognition lives behind
    :class:`IntentRecognizerPort`, so the LLM is fully mockable in tests.
    """

    def __init__(
        self,
        intent_recognizer: IntentRecognizerPort,
        session_store: SessionStore | None = None,
        max_steps: int = 20,
        chat_use_case=None,
    ):
        self.intent_recognizer = intent_recognizer
        self.session_store = session_store or SessionStore(max_steps_per_session=max_steps)
        self.max_steps = max_steps
        # One lock per trace key serializes get->recognize->append so concurrent
        # calls for the same order can't both read identical history (TOCTOU).
        self._locks: dict[str, asyncio.Lock] = {}
        self.chat_use_case = chat_use_case

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

    def _confirmation_required(
        self, action_type: ActionType, input_dto: ExecuteCommandInputDTO
    ) -> bool:
        """Whether *action_type* needs a spoken confirmation for this user.

        Driven by the effective confirm set: the per-user configurable set when
        supplied (``confirm_actions``), else the default outward-facing set
        (``DEFAULT_CONFIRM_ACTIONS``). The recognizer's legacy per-spec flag is
        NOT used to trigger the hold (it would blanket-confirm every TAP_ELEMENT
        and break autonomous navigation); it stays only for back-compat on the wire.
        """
        effective = (
            input_dto.confirm_actions
            if input_dto.confirm_actions is not None
            else DEFAULT_CONFIRM_ACTIONS
        )
        return action_type.value in effective

    def _resolve_pending(
        self,
        input_dto: ExecuteCommandInputDTO,
        session_id: str,
        pending: dict,
        history: list[str],
        step: int,
    ) -> ExecuteCommandOutputDTO:
        """Interpret the user's spoken reply to a pending confirmation."""
        verdict = classify_affirmation(input_dto.text)
        action_type = ActionType.from_string(pending["action_type"])
        parameters = pending.get("parameters", {})

        if verdict == "yes":
            # Confirmed: emit the action so the client executes it, and continue
            # the ReAct loop (record it as a real step).
            self.session_store.clear_pending(session_id)
            rendered = f"Step {step}: {action_type.value} {parameters}"
            self.session_store.append(session_id, rendered)
            task_complete = step >= self.max_steps
            if task_complete:
                self.session_store.reset(session_id)
            return ExecuteCommandOutputDTO(
                success=True,
                reply_text="De acuerdo, lo hago.",
                action_type=action_type.value,
                parameters=parameters,
                confidence=1.0,
                requires_confirmation=False,
                task_complete=task_complete,
                step=step,
            )

        if verdict == "no":
            # Declined: cancel the whole task (the user stopped the sensitive thing).
            self.session_store.reset(session_id)
            return ExecuteCommandOutputDTO(
                success=True,
                reply_text="Entendido, lo cancelo.",
                action_type=ActionType.NONE.value,
                parameters={},
                confidence=0.0,
                requires_confirmation=False,
                task_complete=True,
                step=len(history),
            )

        # Unclear: re-ask, bounded so we don't loop forever waiting.
        reasks = int(pending.get("reasks", 0)) + 1
        if reasks > MAX_CONFIRM_REASKS:
            self.session_store.reset(session_id)
            return ExecuteCommandOutputDTO(
                success=True,
                reply_text="Cancelo por falta de confirmación.",
                action_type=ActionType.NONE.value,
                parameters={},
                confidence=0.0,
                requires_confirmation=False,
                task_complete=True,
                step=len(history),
            )
        self.session_store.set_pending(
            session_id, action_type.value, parameters, reasks=reasks
        )
        return ExecuteCommandOutputDTO(
            success=True,
            reply_text=f"No te he entendido. {confirmation_prompt(action_type, parameters)}",
            action_type=ActionType.NONE.value,
            parameters={},
            confidence=0.0,
            requires_confirmation=False,
            task_complete=False,
            awaiting_confirmation=True,
            step=len(history),
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

    async def _execute_locked(
        self, input_dto: ExecuteCommandInputDTO, session_id: str
    ) -> ExecuteCommandOutputDTO:
        history = self.session_store.get(session_id)
        step = len(history) + 1

        # A confirmation was asked last turn: interpret the user's spoken reply
        # ("sí"/"no"/ambiguous) against the pending action before anything else.
        pending = self.session_store.get_pending(session_id)
        if pending is not None:
            return self._resolve_pending(input_dto, session_id, pending, history, step)

        # Boundary: cap reached before reasoning -> force graceful completion.
        if len(history) >= self.max_steps:
            self.session_store.reset(session_id)
            return ExecuteCommandOutputDTO(
                success=True,
                reply_text="He alcanzado el límite de pasos para esta tarea.",
                action_type=ActionType.NONE.value,
                parameters={},
                confidence=0.0,
                requires_confirmation=False,
                task_complete=True,
                step=len(history),
            )

        # Back-compat: only pass history when present so single-shot callers
        # and recognizers without a history param stay valid.
        if history:
            result = await self.intent_recognizer.recognize(
                input_dto.text,
                session_id=session_id,
                screen=input_dto.screen_elements,
                history=history,
            )
        else:
            result = await self.intent_recognizer.recognize(
                input_dto.text,
                session_id=session_id,
                screen=input_dto.screen_elements,
            )

        action_type = result.action.type

        # Propose-then-confirm: hold sensitive actions and ASK the user out loud
        # instead of executing. The action runs only after a spoken "sí" next
        # turn (resolved by _resolve_pending). action_type=NONE so the client
        # just speaks the question; it must NOT pop its own dialog.
        if result.action.is_executable and self._confirmation_required(
            action_type, input_dto
        ):
            self.session_store.set_pending(
                session_id, action_type.value, result.action.parameters
            )
            return ExecuteCommandOutputDTO(
                success=True,
                reply_text=confirmation_prompt(action_type, result.action.parameters),
                action_type=ActionType.NONE.value,
                parameters={},
                confidence=result.confidence,
                requires_confirmation=False,
                task_complete=False,
                awaiting_confirmation=True,
                step=step,
            )

        reply = result.reply
        if action_type is ActionType.NONE and self.chat_use_case is not None:
            # Conversational turn: return the real grounded chat answer (history +
            # memory + persistence) so the client needs no second StreamChat call.
            try:
                chat_out = await self.chat_use_case.execute(
                    ChatInputDTO(text=input_dto.text, session_id=input_dto.user_id)
                )
                reply = chat_out.text
            except Exception:
                logger.warning(
                    "conversational chat pipeline failed; using recognizer reply",
                    exc_info=True,
                )
        elif not reply and result.action.is_executable:
            # Default spoken confirmation for a bare tool call with no text.
            reply = "De acuerdo."
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
            self.session_store.reset(session_id)

        return ExecuteCommandOutputDTO(
            success=action_type is not ActionType.NONE or bool(reply),
            reply_text=reply,
            action_type=action_type.value,
            parameters=result.action.parameters,
            confidence=result.confidence,
            # Legacy on-wire flag: only emit it for actions that are actually in
            # this user's confirm set. Anything in the set is already intercepted
            # above (held for spoken confirmation), so reaching here means the
            # user opted this action out — never tell the client to pop a dialog.
            requires_confirmation=(
                result.requires_confirmation
                and self._confirmation_required(action_type, input_dto)
            ),
            task_complete=task_complete,
            step=step,
        )
