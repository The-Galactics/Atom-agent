from domain.conversation.models import ChatMessage
from application.agents.state import AgentState
from ports.llm_port import LLMPort
from ports.vector_store_port import VectorStorePort


class GraphNodes:
    def __init__(self, llm_port: LLMPort, vector_store_port: VectorStorePort):
        self.llm = llm_port
        self.vector_store = vector_store_port

    async def retrieve_memory(self, state: AgentState) -> dict:
        """Retrieves semantic memory based on the user input."""
        results = await self.vector_store.search(state["input"])
        context = "\n".join([r.content for r in results])
        return {"context": context}

    async def generate_response(self, state: AgentState) -> dict:
        """Generates a response using Gemma and the retrieved context."""
        system_msg = ChatMessage(
            role="system",
            content=f"Eres Atom. Contexto relevante:\n{state['context']}"
        )
        user_msg = ChatMessage(role="user", content=state["input"])
        
        # Prepare messages including history (simplified for now)
        messages = [system_msg] + state["messages"] + [user_msg]
        
        response = await self.llm.chat(messages)
        return {"response": response, "messages": [user_msg, response]}

    async def store_memory(self, state: AgentState) -> dict:
        """Stores the interaction in the semantic memory."""
        content = f"Usuario: {state['input']}\nAtom: {state['response'].content}"
        await self.vector_store.store(content, {"session_id": state["session_id"]})
        return {}
