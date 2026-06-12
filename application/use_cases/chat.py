from domain.conversation.models import ChatMessage
from ports.history_port import HistoryPort


class ChatUseCase:
    def __init__(self, graph, history_adapter: HistoryPort):
        self.graph = graph
        self.history = history_adapter

    async def execute(self, session_id: str, text: str) -> str:
        # 1. Get history
        history = self.history.get_history(session_id)

        # 2. Run graph
        initial_state = {
            "session_id": session_id,
            "input": text,
            "messages": history,
            "context": "",
            "response": None
        }

        final_state = await self.graph.ainvoke(initial_state)
        
        response = final_state["response"]

        # 3. Update history (the user msg and assistant msg are added by the node)
        for msg in final_state["messages"]:
            self.history.add_message(session_id, msg)

        return response.content
