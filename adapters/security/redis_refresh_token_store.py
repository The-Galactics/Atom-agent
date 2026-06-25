from ports.refresh_token_store_port import RefreshTokenStorePort


class RedisRefreshTokenStore(RefreshTokenStorePort):
    """Redis-backed refresh-token store (revocable, TTL).

    Shared across instances so logout/rotation revoke everywhere. Requires Redis
    6.2+ for ``GETDEL`` (atomic single-use rotation).
    """

    _PREFIX = "atom:refresh:"

    def __init__(self, redis):
        # redis: a redis.asyncio.Redis client.
        self._redis = redis

    def _key(self, token: str) -> str:
        return self._PREFIX + token

    async def save(self, token: str, user_id: str, ttl_seconds: int) -> None:
        await self._redis.set(self._key(token), user_id, ex=ttl_seconds)

    async def pop(self, token: str) -> str | None:
        value = await self._redis.getdel(self._key(token))
        if value is None:
            return None
        return value.decode() if isinstance(value, (bytes, bytearray)) else value

    async def delete(self, token: str) -> None:
        await self._redis.delete(self._key(token))
