from abc import ABC, abstractmethod
from domain.user.models import User


class UserRepositoryPort(ABC):
    # Contract for user persistence and lookup.
    @abstractmethod
    async def find_by_email(self, email: str) -> User | None:
        """Returns the user with this (normalized) email, or None."""
        pass

    @abstractmethod
    async def find_by_id(self, user_id: str) -> User | None:
        """Returns the user with this id, or None."""
        pass

    @abstractmethod
    async def find_by_google_sub(self, google_sub: str) -> User | None:
        """Returns the user linked to this Google subject id, or None."""
        pass

    @abstractmethod
    async def save(self, user: User) -> User:
        """Persists a new user. Raises UserAlreadyExistsError on email conflict."""
        pass

    @abstractmethod
    async def update_password_hash(self, user_id: str, password_hash: str) -> None:
        """Replaces the stored password hash (e.g. after a rehash)."""
        pass

    @abstractmethod
    async def update_settings(self, user_id: str, settings: dict) -> User:
        """Persists the user's synced client settings and returns the updated user."""
        pass

    @abstractmethod
    async def link_google(self, user_id: str, google_sub: str) -> User:
        """Links a Google account to an existing user and returns the updated user."""
        pass
