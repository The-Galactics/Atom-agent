from dataclasses import dataclass


@dataclass
class TokenPair:
    # Result of a successful authentication: a short-lived access token plus a
    # revocable refresh token.
    access_token: str
    refresh_token: str
    expires_in: int        # access-token lifetime in seconds
    user_id: str


@dataclass
class Principal:
    # The authenticated identity derived from a verified access token. This is the
    # ONLY trusted source of user_id for protected requests (never the request body).
    user_id: str
    email: str | None = None


@dataclass
class GoogleIdentity:
    # Verified claims extracted from a Google OIDC ID token. ``sub`` is the stable
    # account identifier (preferred over email, which can change).
    sub: str
    email: str
    name: str | None = None
