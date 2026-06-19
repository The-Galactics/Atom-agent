from application.dtos import (
    ChatInputDTO,
    ExecuteCommandInputDTO,
    ExecuteCommandOutputDTO,
)
from domain.intent.models import ActionType
from ports.intent_port import IntentRecognizerPort


class ExecuteCommandUseCase:
    """Interprets a user order and returns the action the client must run.

    This is the "order" path (gRPC ``ExecuteCommand``). The intent recognizer
    acts purely as a router: if the utterance maps to a device action it is
    returned for the client to execute; otherwise it is a conversational turn
    and — when a chat use case is wired — we delegate to it so the reply gets
    web grounding, memory and history instead of the router's context-free
    answer. Recognition lives behind :class:`IntentRecognizerPort`, so the LLM
    is fully mockable in tests.
    """

    def __init__(self, intent_recognizer: IntentRecognizerPort, chat_use_case=None):
        self.intent_recognizer = intent_recognizer
        # Optional: grounded conversational path for non-action utterances.
        self.chat_use_case = chat_use_case

    async def execute(self, input_dto: ExecuteCommandInputDTO) -> ExecuteCommandOutputDTO:
        result = await self.intent_recognizer.recognize(
            input_dto.text, session_id=input_dto.user_id
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
            # Provide a default spoken confirmation when the model returned a
            # bare tool call with no accompanying text.
            reply = "De acuerdo."

        return ExecuteCommandOutputDTO(
            success=result.action.type is not ActionType.NONE or bool(reply),
            reply_text=reply,
            action_type=result.action.type.value,
            parameters=result.action.parameters,
            confidence=result.confidence,
            requires_confirmation=result.requires_confirmation,
        )
