import asyncio
import time
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


def test_search_filters_by_user_id():
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
    assert dedup_filter.must[0].key == "user_id"
    assert dedup_filter.must[0].match.value == "u9"

    # The stored point carries user_id in its payload (so search can filter it).
    point = a._client.upsert.call_args.kwargs["points"][0]
    assert point.payload["user_id"] == "u9"


def test_search_isolates_by_user():
    """Cross-user isolation: a search for userB must filter by userB's user_id,
    not by any other user's id.  This catches regressions where the filter key
    reverts to 'session_id' or the value is taken from the wrong user."""
    a = _adapter()

    asyncio.run(a.search("q", session_id="userB"))

    flt = a._client.query_points.call_args.kwargs["query_filter"]
    assert isinstance(flt, rest.Filter)
    cond = flt.must[0]
    # Key must be "user_id", not "session_id" or anything else.
    assert cond.key == "user_id"
    # Value must be the *requesting* user, not some other user's id.
    assert cond.match.value == "userB"


def test_store_does_not_block_the_event_loop(monkeypatch):
    from adapters.vector_store.qdrant_adapter import QdrantAdapter

    embed = MagicMock()
    async def _embed(_): return [0.1, 0.2, 0.3]
    embed.embed_text = _embed

    adapter = QdrantAdapter(
        url="http://x", api_key=None, collection_name="c",
        embedding_port=embed, vector_size=3, dedup_threshold=1.0, ttl_days=0,
    )

    fake = MagicMock()
    fake.upsert = MagicMock(side_effect=lambda **k: time.sleep(0.3))  # blocking I/O
    adapter._client = fake
    monkeypatch.setattr(adapter, "_ensure_collection", _noop_async())

    async def scenario():
        # Count only ticks that occur BEFORE store completes.
        # If store blocks the loop, heartbeat cannot tick while store is running
        # and store_done is never set during that window, so 0 ticks are counted.
        ticks_before_done: list[int] = []
        store_done = asyncio.Event()

        async def heartbeat():
            for _ in range(40):
                await asyncio.sleep(0.01)
                if not store_done.is_set():
                    ticks_before_done.append(1)

        async def tracked_store():
            await adapter.store("hello world", {"user_id": "u1"})
            store_done.set()

        await asyncio.gather(tracked_store(), heartbeat())
        return len(ticks_before_done)

    ticks = asyncio.run(scenario())
    # With asyncio.to_thread: store runs in a worker thread (non-blocking),
    # so heartbeat ticks concurrently during the 0.3 s upsert -> ticks >= 15.
    # Without to_thread: store blocks the loop for 0.3 s; heartbeat gets 0
    # ticks before store_done is set -> assertion fails.
    assert ticks >= 15


def _noop_async():
    async def _f(*a, **k): return None
    return _f
