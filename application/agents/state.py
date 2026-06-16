from typing import Annotated, TypedDict, List
from domain.conversation.models import ChatMessage


class AgentState(TypedDict):
    # Shared mutable state passed between LangGraph nodes.
    # Correlation key used across nodes (history + vector-store metadata).
    session_id: str

    # Raw user input that will be routed through retrieve/generate nodes.
    input: str

    # Chat history; annotated for LangGraph to append during execution.
    messages: Annotated[List[ChatMessage], "add"]

    # Retrieved semantic context (built in retrieve_memory).
    context: str

    # Final assistant message (created in generate_response).
    response: ChatMessage | None
