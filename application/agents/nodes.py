import logging

from domain.conversation.models import ChatMessage
from application.agents.state import AgentState
from ports.llm_port import LLMPort
from ports.vector_store_port import VectorStorePort

logger = logging.getLogger("voice_module")


class GraphNodes:
    # LangGraph node implementations for chat orchestration.
    def __init__(self, llm_port: LLMPort, vector_store_port: VectorStorePort,
                 memory_enabled: bool = True):
        self.llm = llm_port
        self.vector_store = vector_store_port
        self.memory_enabled = memory_enabled

    async def retrieve_memory(self, state: AgentState) -> dict:
        """Retrieves semantic memory based on the user input.

        Memory is a best-effort enrichment: if the vector store / embeddings
        are unavailable (Qdrant down, model not downloaded) we log and continue
        with empty context so the LLM can still answer.
        """
        # Skip entirely when memory is disabled — avoids loading the embedding
        # model / hitting Qdrant when no vector store is provisioned.
        if not self.memory_enabled:
            return {"context": ""}
        try:
            results = await self.vector_store.search(state["input"])
            context = "\n".join([r.content for r in results])
        except Exception as exc:
            logger.warning(
                "memory_retrieve_failed session_id=%s error=%s",
                state.get("session_id"),
                exc,
            )
            context = ""
        return {"context": context}

    async def generate_response(self, state: AgentState) -> dict:
        """Generates a response using Gemma and the retrieved context."""
        # System prompt injects retrieved semantic context.
        system_msg = ChatMessage(
            role="system",
            content=f"Eres Atom. Contexto relevante:\n{state['context']}"
        )
        user_msg = ChatMessage(role="user", content=state["input"])

        # Prepare messages including history (simplified for now)
        messages = [system_msg] + state["messages"] + [user_msg]

        response = await self.llm.chat(messages)
        # Return both messages so downstream nodes/use cases can persist them.
        return {"response": response, "messages": [user_msg, response]}

    async def store_memory(self, state: AgentState) -> dict:
        """Stores the interaction in the semantic memory."""
        # Persist a combined user+assistant text into the vector store.
        content = f"Usuario: {state['input']}\nAtom: {state['response'].content}"
        await self.vector_store.store(content, {"session_id": state["session_id"]})
        """Stores the interaction in the semantic memory.

        Best-effort: failures to persist (Qdrant down, embeddings unavailable)
        are logged and swallowed so the chat turn still succeeds.
        """
        if not self.memory_enabled:
            return {}
        try:
            content = f"Usuario: {state['input']}\nAtom: {state['response'].content}"
            await self.vector_store.store(content, {"session_id": state["session_id"]})
        except Exception as exc:
            logger.warning(
                "memory_store_failed session_id=%s error=%s",
                state.get("session_id"),
                exc,
            )
        return {}
