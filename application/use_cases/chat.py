from domain.conversation.models import ChatMessage
from ports.history_port import HistoryPort
from application.dtos import ChatInputDTO, ChatOutputDTO


class ChatUseCase:
    # Coordinates conversational graph execution and session history.
    def __init__(self, graph, history_adapter: HistoryPort):
        # LangGraph workflow + storage of per-session chat history.
        self.graph = graph
        self.history = history_adapter

    async def execute(self, input_dto: ChatInputDTO) -> ChatOutputDTO:
        # 1) Load previous messages for the session.
        history = self.history.get_history(input_dto.session_id)

        # 2) Invoke the orchestration graph (retrieve -> generate -> store).
        initial_state = {
            "session_id": input_dto.session_id,
            "input": input_dto.text,
            "messages": history,
            "context": "",
            "response": None,
            "web_search": input_dto.enable_web_search,
        }
        final_state = await self.graph.ainvoke(initial_state)

        response = final_state["response"]

        # 3) Persist only the NEW messages produced this turn.
        # generate_response returns [user_msg, assistant_msg]; the loaded
        # history was passed into the graph as initial state, so re-persisting
        # the full accumulated `messages` would store every prior message again
        # on each turn (N-fold duplication). Persist just the last two.
        for msg in final_state["messages"][-2:]:
            self.history.add_message(input_dto.session_id, msg)

        return ChatOutputDTO(
            text=response.content,
            session_id=input_dto.session_id
        )
