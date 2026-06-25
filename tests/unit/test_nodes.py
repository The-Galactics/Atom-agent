"""Unit tests for the LangGraph chat nodes (``GraphNodes``).

Uses in-memory fakes for the LLM and vector store so the retrieve/generate/store
logic — including date injection and best-effort memory degradation — is tested
without network or a real Qdrant.
"""

import asyncio

from application.agents.nodes import GraphNodes
from domain.conversation.models import ChatMessage
from domain.memory.models import MemoryEntry
from ports.llm_port import LLMPort
from ports.vector_store_port import VectorStorePort


class FakeLLM(LLMPort):
    def __init__(self, reply="respuesta"):
        self.reply = reply
        self.last_messages = None

    async def chat(self, messages, temperature=0.7, max_tokens=1024):
        self.last_messages = messages
        return ChatMessage(role="assistant", content=self.reply)


class FakeVectorStore(VectorStorePort):
    def __init__(self, results=None, search_exc=None):
        self.results = results or []
        self.search_exc = search_exc
        self.stored = []
        self.last_session_id = None

    async def search(self, query, limit=5, score_threshold=0.5, session_id=None):
        self.last_session_id = session_id
        if self.search_exc:
            raise self.search_exc
        return self.results

    async def store(self, content, metadata):
        self.stored.append((content, metadata))


# --- retrieve_memory --------------------------------------------------------

def test_retrieve_memory_joins_results():
    vs = FakeVectorStore(results=[
        MemoryEntry(content="dato a", metadata={}),
        MemoryEntry(content="dato b", metadata={}),
    ])
    nodes = GraphNodes(FakeLLM(), vs)
    out = asyncio.run(nodes.retrieve_memory({"input": "q", "session_id": "s"}))
    assert out["context"] == "dato a\ndato b"
    # Retrieval is isolated to this session/user.
    assert vs.last_session_id == "s"


def test_retrieve_memory_disabled_returns_empty():
    nodes = GraphNodes(FakeLLM(), FakeVectorStore(), memory_enabled=False)
    out = asyncio.run(nodes.retrieve_memory({"input": "q", "session_id": "s"}))
    assert out["context"] == ""


def test_retrieve_memory_degrades_on_error():
    vs = FakeVectorStore(search_exc=RuntimeError("qdrant down"))
    nodes = GraphNodes(FakeLLM(), vs)
    out = asyncio.run(nodes.retrieve_memory({"input": "q", "session_id": "s"}))
    assert out["context"] == ""


# --- generate_response ------------------------------------------------------

def test_generate_response_injects_date_and_context():
    llm = FakeLLM(reply="hola")
    nodes = GraphNodes(llm, FakeVectorStore(), timezone="America/Bogota")
    state = {"input": "u", "context": "contexto-relevante", "messages": [], "session_id": "s"}
    out = asyncio.run(nodes.generate_response(state))

    assert out["response"].content == "hola"
    assert out["messages"][0].role == "user"
    assert out["messages"][1].role == "assistant"

    system = llm.last_messages[0]
    assert system.role == "system"
    assert "Fecha y hora actuales" in system.content
    assert "contexto-relevante" in system.content


# --- store_memory -----------------------------------------------------------

def _state(text, reply="r"):
    return {"input": text, "session_id": "s",
            "response": ChatMessage(role="assistant", content=reply)}


def test_store_memory_disabled_is_noop():
    vs = FakeVectorStore()
    nodes = GraphNodes(FakeLLM(), vs, memory_enabled=False)
    out = asyncio.run(nodes.store_memory(_state("me llamo Andrés y vivo en Bogotá")))
    assert out == {}
    assert vs.stored == []


def test_store_memory_skips_trivial():
    vs = FakeVectorStore()
    nodes = GraphNodes(FakeLLM(), vs, memory_min_words=4)
    out = asyncio.run(nodes.store_memory(_state("hola")))
    assert out == {}
    assert vs.stored == []


def test_store_memory_persists_memorable_in_background():
    async def scenario():
        vs = FakeVectorStore()
        nodes = GraphNodes(FakeLLM(), vs, memory_min_words=4)
        await nodes.store_memory(_state("me llamo Andrés y vivo en Bogotá", reply="Encantado"))
        # Persistence is fire-and-forget; yield so the background task runs.
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        return vs.stored

    stored = asyncio.run(scenario())
    assert len(stored) == 1
    content, metadata = stored[0]
    assert "me llamo Andrés" in content
    assert "Encantado" in content
    assert metadata == {"user_id": "s"}
