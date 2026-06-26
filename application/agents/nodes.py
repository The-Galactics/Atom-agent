import asyncio
import logging

from domain.conversation.models import ChatMessage
from domain.datetime_context import current_datetime_sentence
from domain.memory.importance import is_memorable
from application.agents.state import AgentState
from ports.llm_port import LLMPort
from ports.vector_store_port import VectorStorePort

logger = logging.getLogger("voice_module")


class GraphNodes:
    # LangGraph node implementations for chat orchestration.
    def __init__(self, llm_port: LLMPort, vector_store_port: VectorStorePort,
                 memory_enabled: bool = True, memory_min_words: int = 4,
                 timezone: str = "America/Bogota"):
        self.llm = llm_port
        self.vector_store = vector_store_port
        self.memory_enabled = memory_enabled
        self.memory_min_words = memory_min_words
        self.timezone = timezone
        # Keeps strong refs to fire-and-forget store tasks so they aren't GC'd.
        self._bg_tasks: set[asyncio.Task] = set()

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
            # Isolate retrieval to this session/user — never read another user's memory.
            results = await self.vector_store.search(
                state["input"], session_id=state.get("session_id")
            )
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
        """Generates a response using Gemini and the retrieved context."""
        # System prompt injects the current date/time (the model has no clock)
        # plus any retrieved semantic context.
        system_msg = ChatMessage(
            role="system",
            content=(
                f"Eres Atom. {current_datetime_sentence(self.timezone)}\n"
                f"Contexto relevante:\n{state['context']}"
            )
        )
        user_msg = ChatMessage(role="user", content=state["input"])

        # Prepare messages including history (simplified for now)
        messages = [system_msg] + state["messages"] + [user_msg]

        response = await self.llm.chat(messages)
        # Return both messages so downstream nodes/use cases can persist them.
        return {"response": response, "messages": [user_msg, response]}

    async def store_memory(self, state: AgentState) -> dict:
        """Stores the interaction in the semantic memory.

        Best-effort: failures to persist (Qdrant down, embeddings unavailable)
        are logged and swallowed so the chat turn still succeeds.
        """
        # Skip entirely when memory is disabled — avoids embedding calls /
        # hitting Qdrant when no vector store is provisioned.
        if not self.memory_enabled:
            return {}
        # #1 Importance filter — don't persist greetings/smalltalk; keep the
        # vector store small and relevant. Judged on the user's utterance.
        if not is_memorable(state["input"], self.memory_min_words):
            logger.info("memory_skip_trivial session_id=%s", state.get("session_id"))
            return {}
        # Persist in the background so the chat response isn't blocked on the
        # embedding + vector upsert round-trips (saves ~0.2-0.4s per turn).
        content = f"Usuario: {state['input']}\nAtom: {state['response'].content}"
        task = asyncio.create_task(self._persist(content, state["session_id"]))
        self._bg_tasks.add(task)
        task.add_done_callback(self._bg_tasks.discard)
        return {}

    async def _persist(self, content: str, session_id: str) -> None:
        """Embeds + upserts the interaction off the request path. Best-effort."""
        try:
            await self.vector_store.store(content, {"user_id": session_id})
        except Exception as exc:
            logger.warning("memory_store_failed session_id=%s error=%s", session_id, exc)
