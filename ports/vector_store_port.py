from abc import ABC, abstractmethod
from domain.memory.models import MemoryEntry


class VectorStorePort(ABC):
    # Contract for semantic memory persistence and retrieval.
    @abstractmethod
    async def store(self, content: str, metadata: dict) -> None:
        """Stores a memory entry in the vector database."""
        pass

    @abstractmethod
    async def search(
        self, query: str, limit: int = 5, score_threshold: float = 0.5,
        session_id: str | None = None,
    ) -> list[MemoryEntry]:
        """Searches for relevant memory entries by semantic similarity.

        When ``session_id`` is given, results are restricted to that session/user
        (multi-tenant isolation) — a user never retrieves another user's memory.
        """
        pass
