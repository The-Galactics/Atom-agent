import asyncio

from infrastructure.container import AppContainer


class _FakeRepo:
    def __init__(self):
        self.calls = 0

    async def ensure_indexes(self):
        self.calls += 1


def test_ensure_auth_indexes_calls_repo_when_present():
    repo = _FakeRepo()
    container = AppContainer.__new__(AppContainer)   # bypass full wiring
    container.user_repository = repo
    asyncio.run(container.ensure_auth_indexes())
    assert repo.calls == 1


def test_ensure_auth_indexes_noop_when_auth_disabled():
    container = AppContainer.__new__(AppContainer)
    container.user_repository = None
    asyncio.run(container.ensure_auth_indexes())   # must not raise


class _BrokenRepo:
    """Fake repo whose ensure_indexes always raises (simulates MongoDB down)."""

    async def ensure_indexes(self):
        raise RuntimeError("mongo connection refused")


def test_ensure_auth_indexes_swallows_exception_on_failure():
    """If ensure_indexes raises, ensure_auth_indexes must NOT propagate the error.

    MongoDB being unreachable at startup must not abort the FastAPI lifespan;
    voice/chat endpoints should still come up (best-effort index creation).
    """
    repo = _BrokenRepo()
    container = AppContainer.__new__(AppContainer)
    container.user_repository = repo
    # Must complete without raising — any exception means the test fails.
    asyncio.run(container.ensure_auth_indexes())
