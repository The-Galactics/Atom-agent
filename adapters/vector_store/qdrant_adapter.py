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
        vector_size: int = 3072,
    ):
        self.url = url
        self.api_key = api_key
        self.collection_name = collection_name
        self.embedding_port = embedding_port
        # Embedding dimensionality; must match the configured embedding model.
        self.vector_size = vector_size
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
        # Use the private ``_client`` here (not the ``client`` property) because
        # this runs from inside the property after ``_client`` is assigned;
        # referencing the property would recurse back into ``_ensure_collection``.
        try:
            collection_info = self._client.get_collection(self.collection_name)
            current_size = collection_info.config.params.vectors.size
            if current_size != self.vector_size:
                print(f"Dimension mismatch (expected {self.vector_size}, got {current_size}). Recreating collection...")
                self._client.delete_collection(self.collection_name)
                self._create_collection()
        except Exception:
            # Collection does not exist
            self._create_collection()

    def _create_collection(self):
        self._client.create_collection(
            collection_name=self.collection_name,
            vectors_config=rest.VectorParams(
                size=self.vector_size, distance=rest.Distance.COSINE
            ),
        )
        # Index created_at so TTL pruning (delete-by-range) stays efficient, and
        # session_id so the per-user isolation filter stays fast.
        try:
            self._client.create_payload_index(
                collection_name=self.collection_name,
                field_name="created_at",
                field_schema=rest.PayloadSchemaType.INTEGER,
            )
            self._client.create_payload_index(
                collection_name=self.collection_name,
                field_name="session_id",
                field_schema=rest.PayloadSchemaType.KEYWORD,
            )
        except Exception as exc:  # non-fatal: filtering/pruning still works without it
            logger.warning("qdrant_index_failed error=%s", exc)

    async def store(self, content: str, metadata: dict) -> None:
        # Embed content once; reuse the vector for dedup and upsert.
        vector = await self.embedding_port.embed_text(content)

        # #2 Dedup: skip storing a near-duplicate within the SAME session.
        if self.dedup_threshold < 1.0 and self._is_duplicate(vector, metadata.get("session_id")):
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

    def _is_duplicate(self, vector: list[float], session_id: str | None = None) -> bool:
        # A near-duplicate exists if the closest point in the SAME session clears
        # the dedup threshold.
        try:
            hits = self.client.query_points(
                collection_name=self.collection_name,
                query=vector,
                limit=1,
                score_threshold=self.dedup_threshold,
                query_filter=self._session_filter(session_id),
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

    def _session_filter(self, session_id: str | None):
        # Restrict a query to one session/user, or None for an unfiltered query.
        if not session_id:
            return None
        return rest.Filter(
            must=[rest.FieldCondition(
                key="session_id", match=rest.MatchValue(value=session_id))]
        )

    async def search(
        self, query: str, limit: int = 5, score_threshold: float = 0.5,
        session_id: str | None = None,
    ) -> list[MemoryEntry]:
        # Embed query and return mapped memory entries, isolated by session_id so
        # a user never retrieves another user's memory.
        vector = await self.embedding_port.embed_text(query)
        results = self.client.query_points(
            collection_name=self.collection_name,
            query=vector,
            limit=limit,
            score_threshold=score_threshold,
            query_filter=self._session_filter(session_id),
        ).points

        return [
            MemoryEntry(
                content=res.payload.get("content", ""),
                metadata={k: v for k, v in res.payload.items() if k != "content"},
                score=res.score,
            )
            for res in results
        ]
