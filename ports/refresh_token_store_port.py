from abc import ABC, abstractmethod


class RefreshTokenStorePort(ABC):
    # Contract for the revocable refresh-token store (TTL-backed). Maps an opaque
    # refresh token to the user it belongs to.
    @abstractmethod
    async def save(self, token: str, user_id: str, ttl_seconds: int) -> None:
        """Stores the token -> user_id mapping with an expiry."""
        pass

    @abstractmethod
    async def pop(self, token: str) -> str | None:
        """Atomically returns and deletes the user_id for the token (single-use), or None."""
        pass

    @abstractmethod
    async def delete(self, token: str) -> None:
        """Revokes a token. No-op if absent."""
        pass
