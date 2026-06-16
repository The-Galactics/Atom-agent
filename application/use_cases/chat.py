from domain.conversation.models import ChatMessage
from ports.history_port import HistoryPort


class ChatUseCase:
    # Coordinates conversational graph execution and session history.
    def __init__(self, graph, history_adapter: HistoryPort):
        # LangGraph workflow + storage of per-session chat history.
        self.graph = graph
        self.history = history_adapter

    async def execute(self, session_id: str, text: str) -> str:
        # 1) Load previous messages for the session.
        history = self.history.get_history(session_id)

        # 2) Invoke the orchestration graph (retrieve -> generate -> store).
        initial_state = {
            "session_id": session_id,
            "input": text,
            "messages": history,
            "context": "",
            "response": None
        }
        final_state = await self.graph.ainvoke(initial_state)

        response = final_state["response"]

        # 3) Persist messages returned by the graph node(s).
        for msg in final_state["messages"]:
            self.history.add_message(session_id, msg)

        # Response is expected to be created by the graph's generate node.
        return response.content
