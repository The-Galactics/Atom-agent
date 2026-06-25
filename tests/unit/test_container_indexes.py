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
