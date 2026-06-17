import logging
import time
import uuid
from qdrant_client import QdrantClient
from qdrant_client.http import models as rest
from ports.embedding_port import EmbeddingPort

from domain.memory.models import MemoryEntry
from ports.vector_store_port import VectorStorePort

logger = logging.getLogger("voice_module")


class QdrantAdapter(VectorStorePort):
    """Vector store adapter backed by Qdrant.

    The Qdrant client connection and collection bootstrap are performed lazily
    on first use rather than in ``__init__`` so that an unreachable Qdrant
    instance never blocks startup. Failures raised here are expected to be
    caught at the node/use-case boundary so chat can degrade to LLM-only
    (no long-term memory) instead of crashing.
    """

    def __init__(
        self,
        url: str,
        api_key: str | None,
        collection_name: str,
        embedding_port: EmbeddingPort,
        dedup_threshold: float = 0.95,
        ttl_days: int = 30,
        prune_every: int = 20,
    ):
        self.url = url
        self.api_key = api_key
        self.collection_name = collection_name
        self.embedding_port = embedding_port
        # Memory-hygiene knobs (see Settings). dedup_threshold >= 1.0 disables
        # dedup; ttl_days <= 0 disables TTL pruning.
        self.dedup_threshold = dedup_threshold
        self.ttl_seconds = ttl_days * 86400 if ttl_days and ttl_days > 0 else 0
        self.prune_every = max(1, prune_every)
        self._store_count = 0
        self._client: QdrantClient | None = None

    @property
    def client(self) -> QdrantClient:
        if self._client is None:
            self._client = QdrantClient(url=self.url, api_key=self.api_key)
            self._ensure_collection()
        return self._client

    def _ensure_collection(self):
        # Verify the collection exists and has the expected vector dimension.
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
        # Index created_at so TTL pruning (delete-by-range) stays efficient.
        try:
            self.client.create_payload_index(
                collection_name=self.collection_name,
                field_name="created_at",
                field_schema=rest.PayloadSchemaType.INTEGER,
            )
        except Exception as exc:  # non-fatal: pruning still works without it
            logger.warning("qdrant_index_failed error=%s", exc)

    async def store(self, content: str, metadata: dict) -> None:
        # Embed content once; reuse the vector for dedup and upsert.
        vector = self.embedding_port.embed_text(content)

        # #2 Dedup: skip storing a near-duplicate of an existing memory.
        if self.dedup_threshold < 1.0 and self._is_duplicate(vector):
            logger.info("memory_dedup_skipped session_id=%s", metadata.get("session_id"))
            return

        # Deterministic id on content+session so exact repeats collapse on upsert.
        point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, content + str(metadata)))
        self.client.upsert(
            collection_name=self.collection_name,
            points=[
                rest.PointStruct(
                    id=point_id,
                    vector=vector,
                    payload={"content": content, "created_at": int(time.time()), **metadata},
                )
            ],
        )

        # #3 TTL: prune expired memories every `prune_every` stores (throttled).
        self._store_count += 1
        if self.ttl_seconds > 0 and self._store_count % self.prune_every == 0:
            self._prune_expired()

    def _is_duplicate(self, vector: list[float]) -> bool:
        # A near-duplicate exists if the closest point clears the dedup threshold.
        try:
            hits = self.client.query_points(
                collection_name=self.collection_name,
                query=vector,
                limit=1,
                score_threshold=self.dedup_threshold,
            ).points
            return bool(hits)
        except Exception:
            return False

    def _prune_expired(self) -> None:
        # Delete memories older than the TTL window.
        cutoff = int(time.time()) - self.ttl_seconds
        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=rest.FilterSelector(
                    filter=rest.Filter(
                        must=[rest.FieldCondition(
                            key="created_at", range=rest.Range(lt=cutoff)
                        )]
                    )
                ),
            )
            logger.info("memory_pruned cutoff=%s", cutoff)
        except Exception as exc:
            logger.warning("memory_prune_failed error=%s", exc)

    async def search(
        self, query: str, limit: int = 5, score_threshold: float = 0.5
    ) -> list[MemoryEntry]:
        # Embed query and return mapped memory entries.
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
