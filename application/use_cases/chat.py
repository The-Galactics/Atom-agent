from domain.conversation.models import ChatMessage
from ports.history_port import HistoryPort
from application.dtos import ChatInputDTO, ChatOutputDTO


class ChatUseCase:
    def __init__(self, graph, history_adapter: HistoryPort):
        self.graph = graph
        self.history = history_adapter

    async def execute(self, input_dto: ChatInputDTO) -> ChatOutputDTO:
        # 1. Get history
        history = self.history.get_history(input_dto.session_id)

        # 2. Run graph
        initial_state = {
            "session_id": input_dto.session_id,
            "input": input_dto.text,
            "messages": history,
            "context": "",
            "response": None
        }

        final_state = await self.graph.ainvoke(initial_state)
        
        response = final_state["response"]

        # 3. Update history (the user msg and assistant msg are added by the node)
        for msg in final_state["messages"]:
            self.history.add_message(input_dto.session_id, msg)

        return ChatOutputDTO(
            text=response.content,
            session_id=input_dto.session_id
        )
