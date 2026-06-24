from application.agents.session_store import SessionStore
from application.dtos import ExecuteCommandInputDTO, ExecuteCommandOutputDTO
from domain.intent.models import ActionType
from ports.intent_port import IntentRecognizerPort

# Prior steps that must match the current action before the loop is "stuck".
# 2 => 3 identical actions in a row; tolerates one transient repeat.
STUCK_REPEAT_THRESHOLD = 2


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
    ):
        self.intent_recognizer = intent_recognizer
        self.session_store = session_store or SessionStore(max_steps_per_session=max_steps)
        self.max_steps = max_steps

    async def execute(self, input_dto: ExecuteCommandInputDTO) -> ExecuteCommandOutputDTO:
        session_id = input_dto.user_id
        # TODO(cross-order): trace is keyed by user_id and only cleared on
        # completion (or TTL/LRU). An order abandoned mid-loop leaks its trace
        # into the user's next order. Future fix: scope the trace to a per-order id.
        history = self.session_store.get(session_id)
        step = len(history) + 1

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

        # Conversational turn (no device action): route through the grounded
        # chat path so the user gets live web info + memory, not the router's
        # bare reply. Falls back to the router's reply if chat isn't wired.
        if result.action.type is ActionType.NONE and self.chat_use_case is not None:
            chat_output = await self.chat_use_case.execute(
                ChatInputDTO(text=input_dto.text, session_id=input_dto.user_id)
            )
            return ExecuteCommandOutputDTO(
                success=bool(chat_output.text),
                reply_text=chat_output.text,
                action_type=ActionType.NONE.value,
                parameters={},
                confidence=result.confidence,
                requires_confirmation=False,
            )

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
            self.session_store.reset(session_id)

        return ExecuteCommandOutputDTO(
            success=action_type is not ActionType.NONE or bool(reply),
            reply_text=reply,
            action_type=action_type.value,
            parameters=result.action.parameters,
            confidence=result.confidence,
            requires_confirmation=result.requires_confirmation,
            task_complete=task_complete,
            step=step,
        )
