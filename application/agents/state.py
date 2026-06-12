from typing import Annotated, TypedDict, List
from domain.conversation.models import ChatMessage


class AgentState(TypedDict):
    session_id: str
    input: str
    messages: Annotated[List[ChatMessage], "add"]
    context: str
    response: ChatMessage | None
