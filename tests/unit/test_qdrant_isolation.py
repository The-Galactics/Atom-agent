import asyncio
from unittest.mock import MagicMock

from qdrant_client.http import models as rest

from adapters.vector_store.qdrant_adapter import QdrantAdapter
from ports.embedding_port import EmbeddingPort


class FakeEmbed(EmbeddingPort):
    async def embed_text(self, text):
        return [0.1, 0.2, 0.3]

    async def embed_documents(self, texts):
        return [[0.1, 0.2, 0.3] for _ in texts]


def _adapter() -> QdrantAdapter:
    a = QdrantAdapter(
        url="x", api_key=None, collection_name="c",
        embedding_port=FakeEmbed(), vector_size=3,
    )
    # Bypass the real QdrantClient + collection bootstrap.
    a._client = MagicMock()
    a._client.query_points.return_value.points = []
    return a


def test_search_filters_by_session_id():
    a = _adapter()
    asyncio.run(a.search("q", session_id="u1"))
    flt = a._client.query_points.call_args.kwargs["query_filter"]
    assert isinstance(flt, rest.Filter)
    cond = flt.must[0]
    assert cond.key == "user_id"
    assert cond.match.value == "u1"


def test_search_without_session_id_has_no_filter():
    a = _adapter()
    asyncio.run(a.search("q"))
    assert a._client.query_points.call_args.kwargs["query_filter"] is None


def test_store_dedup_is_session_scoped_and_payload_tagged():
    a = _adapter()
    a._client.query_points.return_value.points = []  # no duplicate -> proceeds to upsert
    asyncio.run(a.store("me llamo Andrés y vivo en Bogotá", {"user_id": "u9"}))

    # The dedup lookup was scoped to the same session.
    dedup_filter = a._client.query_points.call_args_list[0].kwargs["query_filter"]
    assert dedup_filter.must[0].match.value == "u9"

    # The stored point carries user_id in its payload (so search can filter it).
    point = a._client.upsert.call_args.kwargs["points"][0]
    assert point.payload["user_id"] == "u9"
