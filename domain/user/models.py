from dataclasses import dataclass, field
from datetime import datetime, timezone
import uuid


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class User:
    """A user account.

    Credentials are never stored in plaintext: ``password_hash`` holds an
    Argon2id hash, or ``None`` for accounts that only authenticate via Google.
    ``auth_providers`` records the linked methods (``"password"`` / ``"google"``).
    """
    email: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    password_hash: str | None = None
    google_sub: str | None = None
    auth_providers: list[str] = field(default_factory=list)
    display_name: str | None = None
    active: bool = True
    settings: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)

    @classmethod
    def new(cls, email: str, password_hash: str, display_name: str | None = None) -> "User":
        # Email/password account.
        return cls(
            email=email,
            password_hash=password_hash,
            display_name=display_name,
            auth_providers=["password"],
        )

    @classmethod
    def federated(cls, email: str, google_sub: str, display_name: str | None = None) -> "User":
        # Google-only account (no password).
        return cls(
            email=email,
            google_sub=google_sub,
            display_name=display_name,
            auth_providers=["google"],
        )
