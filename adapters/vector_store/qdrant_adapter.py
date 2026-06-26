import asyncio
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
        vector_size: int = 0,
    ):
        self.url = url
        self.api_key = api_key
        self.collection_name = collection_name
        self.embedding_port = embedding_port
        # Embedding dimensionality. 0 = auto-detect from the first real embedding
        # (so the collection always matches the model and never mismatches —
        # the root cause of the previous "embeddings failing"). A positive value
        # pins the size explicitly.
        self.vector_size = vector_size
        # Memory-hygiene knobs (see Settings). dedup_threshold >= 1.0 disables
        # dedup; ttl_days <= 0 disables TTL pruning.
        self.dedup_threshold = dedup_threshold
        self.ttl_seconds = ttl_days * 86400 if ttl_days and ttl_days > 0 else 0
        self.prune_every = max(1, prune_every)
        self._store_count = 0
        self._client: QdrantClient | None = None
        self._collection_ready = False

    @property
    def client(self) -> QdrantClient:
        # Lazily create the client only. Collection bootstrap is deferred to the
        # async ``_ensure_collection`` so the true vector dimension can be taken
        # from a real embedding instead of a (possibly wrong) configured number.
        if self._client is None:
            self._client = QdrantClient(url=self.url, api_key=self.api_key)
        return self._client

    async def _ensure_collection(self, dim: int) -> None:
        # Idempotent: create the collection on first use, sized to the model's
        # actual embedding dimension (``vector_size`` when pinned, else ``dim``).
        if self._collection_ready:
            return
        target = self.vector_size if self.vector_size else dim
        client = self.client
        try:
            collection_info = client.get_collection(self.collection_name)
            current_size = collection_info.config.params.vectors.size
            if current_size != target:
                logger.warning(
                    "qdrant_dim_mismatch collection=%s expected=%s got=%s recreating",
                    self.collection_name, target, current_size,
                )
                client.delete_collection(self.collection_name)
                self._create_collection(target)
        except Exception:
            # Collection does not exist yet.
            self._create_collection(target)
        self.vector_size = target
        self._collection_ready = True

    def _create_collection(self, size: int) -> None:
        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=rest.VectorParams(
                size=size, distance=rest.Distance.COSINE
            ),
        )
        # Index created_at so TTL pruning (delete-by-range) stays efficient, and
        # user_id so the per-user isolation filter stays fast.
        try:
            self.client.create_payload_index(
                collection_name=self.collection_name,
                field_name="created_at",
                field_schema=rest.PayloadSchemaType.INTEGER,
            )
            self._client.create_payload_index(
                collection_name=self.collection_name,
                field_name="user_id",
                field_schema=rest.PayloadSchemaType.KEYWORD,
            )
        except Exception as exc:  # non-fatal: filtering/pruning still works without it
            logger.warning("qdrant_index_failed error=%s", exc)

    async def store(self, content: str, metadata: dict) -> None:
        # Embed content once; reuse the vector for dedup and upsert.
        vector = await self.embedding_port.embed_text(content)
        # Bootstrap the collection to the embedding's real dimension on first use.
        await self._ensure_collection(len(vector))

        # #2 Dedup: skip storing a near-duplicate within the SAME session.
        if self.dedup_threshold < 1.0 and await self._is_duplicate(vector, metadata.get("user_id")):
            logger.info("memory_dedup_skipped user_id=%s", metadata.get("user_id"))
            return

        # Deterministic id on content+session so exact repeats collapse on upsert.
        point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, content + str(metadata)))
        await asyncio.to_thread(
            self.client.upsert,
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
            await self._prune_expired()

    async def _is_duplicate(self, vector: list[float], session_id: str | None = None) -> bool:
        # A near-duplicate exists if the closest point in the SAME session clears
        # the dedup threshold.
        try:
            hits = (await asyncio.to_thread(
                self.client.query_points,
                collection_name=self.collection_name,
                query=vector,
                limit=1,
                score_threshold=self.dedup_threshold,
                query_filter=self._session_filter(session_id),
            )).points
            return bool(hits)
        except Exception:
            return False

    async def _prune_expired(self) -> None:
        # Delete memories older than the TTL window.
        cutoff = int(time.time()) - self.ttl_seconds
        try:
            await asyncio.to_thread(
                self.client.delete,
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
                key="user_id", match=rest.MatchValue(value=session_id))]
        )

    async def search(
        self, query: str, limit: int = 5, score_threshold: float = 0.5,
        session_id: str | None = None,
    ) -> list[MemoryEntry]:
        # Embed query and return mapped memory entries, isolated by session_id so
        # a user never retrieves another user's memory.
        vector = await self.embedding_port.embed_text(query)
        # Bootstrap the collection to the embedding's real dimension on first use.
        await self._ensure_collection(len(vector))
        results = (await asyncio.to_thread(
            self.client.query_points,
            collection_name=self.collection_name,
            query=vector,
            limit=limit,
            score_threshold=score_threshold,
            query_filter=self._session_filter(session_id),
        )).points

        return [
            MemoryEntry(
                content=res.payload.get("content", ""),
                metadata={k: v for k, v in res.payload.items() if k != "content"},
                score=res.score,
            )
            for res in results
        ]
