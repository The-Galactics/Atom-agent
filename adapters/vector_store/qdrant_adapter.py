import uuid
from qdrant_client import QdrantClient
from qdrant_client.http import models as rest
from ports.embedding_port import EmbeddingPort

from domain.memory.models import MemoryEntry
from ports.vector_store_port import VectorStorePort


class QdrantAdapter(VectorStorePort):
    def __init__(
        self,
        url: str,
        api_key: str | None,
        collection_name: str,
        embedding_port: EmbeddingPort,
    ):
        self.client = QdrantClient(url=url, api_key=api_key)
        self.collection_name = collection_name
        self.embedding_port = embedding_port
        self._ensure_collection()

    def _ensure_collection(self):
        try:
            collection_info = self.client.get_collection(self.collection_name)
            current_size = collection_info.config.params.vectors.size
            if current_size != 3072:
                print(f"Dimension mismatch (expected 3072, got {current_size}). Recreating collection...")
                self.client.delete_collection(self.collection_name)
                self._create_collection()
        except Exception:
            # Collection does not exist
            self._create_collection()

    def _create_collection(self):
        # gemini-embedding-2 has 3072 dimensions
        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=rest.VectorParams(
                size=3072, distance=rest.Distance.COSINE
            ),
        )

    async def store(self, content: str, metadata: dict) -> None:
        vector = self.embedding_port.embed_text(content)
        # Generate a deterministic UUID based on the content
        point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, content + str(metadata)))
        self.client.upsert(
            collection_name=self.collection_name,
            points=[
                rest.PointStruct(
                    id=point_id,
                    vector=vector,
                    payload={"content": content, **metadata},
                )
            ],
        )

    async def search(
        self, query: str, limit: int = 5, score_threshold: float = 0.5
    ) -> list[MemoryEntry]:
        vector = self.embedding_port.embed_text(query)
        results = self.client.query_points(
            collection_name=self.collection_name,
            query=vector,
            limit=limit,
            score_threshold=score_threshold,
        ).points

        return [
            MemoryEntry(
                content=res.payload.get("content", ""),
                metadata={k: v for k, v in res.payload.items() if k != "content"},
                score=res.score,
            )
            for res in results
        ]
