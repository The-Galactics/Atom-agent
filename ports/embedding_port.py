from abc import ABC, abstractmethod


class EmbeddingPort(ABC):
    @abstractmethod
    def embed_text(self, text: str) -> list[float]:
        """Generates an embedding vector for the given text."""
        pass

    @abstractmethod
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Generates embedding vectors for a list of documents."""
        pass
