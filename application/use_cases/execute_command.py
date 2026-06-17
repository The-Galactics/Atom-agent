from application.dtos import ExecuteCommandInputDTO, ExecuteCommandOutputDTO
from domain.intent.models import ActionType
from ports.intent_port import IntentRecognizerPort


class ExecuteCommandUseCase:
    """Interprets a user order and returns the action the client must run.

    This is the "order" path (gRPC ``ExecuteCommand``), kept separate from the
    free-form conversational chat flow. Recognition lives behind
    :class:`IntentRecognizerPort`, so the LLM is fully mockable in tests.
    """

    def __init__(self, intent_recognizer: IntentRecognizerPort):
        self.intent_recognizer = intent_recognizer

    async def execute(self, input_dto: ExecuteCommandInputDTO) -> ExecuteCommandOutputDTO:
        result = await self.intent_recognizer.recognize(
            input_dto.text, session_id=input_dto.user_id
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
