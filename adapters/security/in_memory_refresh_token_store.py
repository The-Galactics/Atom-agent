import time

from ports.refresh_token_store_port import RefreshTokenStorePort


class InMemoryRefreshTokenStore(RefreshTokenStorePort):
    """Process-local refresh-token store.

    Fine for development, tests and single-instance deployments. Use
    ``RedisRefreshTokenStore`` for multi-instance/production (shared revocation).
    """

    def __init__(self):
        # token -> (user_id, expiry_epoch_seconds)
        self._data: dict[str, tuple[str, float]] = {}

    async def save(self, token: str, user_id: str, ttl_seconds: int) -> None:
        self._data[token] = (user_id, time.time() + ttl_seconds)

    async def pop(self, token: str) -> str | None:
        entry = self._data.pop(token, None)
        if entry is None:
            return None
        user_id, expiry = entry
        if time.time() >= expiry:
            return None  # expired -> already removed by pop
        return user_id

    async def delete(self, token: str) -> None:
        self._data.pop(token, None)
