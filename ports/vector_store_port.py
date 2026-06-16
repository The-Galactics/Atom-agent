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
        self, query: str, limit: int = 5, score_threshold: float = 0.5
    ) -> list[MemoryEntry]:
        """Searches for relevant memory entries based on semantic similarity."""
        pass
