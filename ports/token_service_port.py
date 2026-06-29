from abc import ABC, abstractmethod
from domain.auth.models import Principal, TokenPair


class TokenServicePort(ABC):
    # Contract for issuing and validating session tokens. The access token is
    # short-lived and stateless; the refresh token is revocable (TTL-backed).
    @abstractmethod
    async def issue_pair(self, user_id: str, email: str | None = None) -> TokenPair:
        """Issues a new (access, refresh) token pair and persists the refresh token."""
        pass

    @abstractmethod
    def verify_access(self, access_token: str) -> Principal | None:
        """Returns the Principal for a valid access token, or None if invalid/expired."""
        pass

    @abstractmethod
    async def rotate(self, refresh_token: str) -> TokenPair | None:
        """Validates and rotates a refresh token (invalidating the old one), or None."""
        pass

    @abstractmethod
    async def revoke(self, refresh_token: str) -> None:
        """Revokes a refresh token (logout). No-op if it does not exist."""
        pass
