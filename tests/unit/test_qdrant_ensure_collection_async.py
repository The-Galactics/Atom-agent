import asyncio
from unittest.mock import MagicMock
from adapters.vector_store.qdrant_adapter import QdrantAdapter


def _adapter_with_mock_client():
    a = QdrantAdapter.__new__(QdrantAdapter)  # bypass real client construction
    # client is a @property backed by self._client — set the backing attribute
    a._client = MagicMock()
    a.collection_name = "skills"
    a.vector_size = 0
    a._collection_ready = False
    a._ensure_lock = asyncio.Lock()
    return a


def test_concurrent_cold_start_creates_collection_once(monkeypatch):
    a = _adapter_with_mock_client()
    a._client.get_collection.side_effect = Exception("not found")
    created = {"n": 0}

    def fake_create(target):
        created["n"] += 1

    monkeypatch.setattr(a, "_create_collection", fake_create)

    async def run():
        await asyncio.gather(a._ensure_collection(8), a._ensure_collection(8))

    asyncio.run(run())
    assert created["n"] == 1
    assert a._collection_ready is True


def test_ensure_collection_offloads_blocking_get_to_thread(monkeypatch):
    a = _adapter_with_mock_client()
    a._client.get_collection.return_value = MagicMock(
        config=MagicMock(params=MagicMock(vectors=MagicMock(size=8))))

    calls = {"to_thread": 0}
    real_to_thread = asyncio.to_thread

    async def spy(fn, *args, **kwargs):
        calls["to_thread"] += 1
        return await real_to_thread(fn, *args, **kwargs)

    monkeypatch.setattr("adapters.vector_store.qdrant_adapter.asyncio.to_thread", spy)
    asyncio.run(a._ensure_collection(8))

    assert calls["to_thread"] >= 1            # blocking I/O offloaded
    assert a._collection_ready is True        # behavior preserved
    a._client.get_collection.assert_called_once_with("skills")
