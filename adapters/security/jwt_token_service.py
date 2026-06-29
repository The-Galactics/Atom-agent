import secrets
import time

import jwt  # PyJWT

from domain.auth.models import Principal, TokenPair
from ports.token_service_port import TokenServicePort
from ports.refresh_token_store_port import RefreshTokenStorePort


class JwtTokenService(TokenServicePort):
    """Issues a short-lived signed access token (JWT) plus an opaque, revocable
    refresh token (kept in a TTL store).

    Defaults to HS256 with a shared secret. For asymmetric signing (RS256) pass
    ``algorithm="RS256"`` with ``signing_key``/``verifying_key`` set to the
    private/public PEM keys.
    """

    def __init__(self, refresh_store: RefreshTokenStorePort, signing_key: str,
                 verifying_key: str | None = None, algorithm: str = "HS256",
                 access_ttl_seconds: int = 900, refresh_ttl_seconds: int = 2_592_000,
                 issuer: str = "atom-agent"):
        self._store = refresh_store
        self._signing_key = signing_key
        # For HS256 the verifying key IS the signing secret.
        self._verifying_key = verifying_key or signing_key
        self._alg = algorithm
        self._access_ttl = access_ttl_seconds
        self._refresh_ttl = refresh_ttl_seconds
        self._issuer = issuer

    async def issue_pair(self, user_id: str, email: str | None = None) -> TokenPair:
        now = int(time.time())
        payload = {
            "sub": user_id,
            "email": email,
            "type": "access",
            "iss": self._issuer,
            "iat": now,
            "exp": now + self._access_ttl,
        }
        access = jwt.encode(payload, self._signing_key, algorithm=self._alg)
        refresh = secrets.token_urlsafe(48)
        await self._store.save(refresh, user_id, self._refresh_ttl)
        return TokenPair(
            access_token=access,
            refresh_token=refresh,
            expires_in=self._access_ttl,
            user_id=user_id,
        )

    def verify_access(self, access_token: str) -> Principal | None:
        try:
            payload = jwt.decode(
                access_token,
                self._verifying_key,
                algorithms=[self._alg],
                issuer=self._issuer,
                options={"require": ["exp", "sub", "iss"]},
            )
        except jwt.PyJWTError:
            return None
        if payload.get("type") != "access":
            return None
        return Principal(user_id=payload["sub"], email=payload.get("email"))

    async def rotate(self, refresh_token: str) -> TokenPair | None:
        user_id = await self._store.pop(refresh_token)
        if user_id is None:
            return None
        return await self.issue_pair(user_id)

    async def revoke(self, refresh_token: str) -> None:
        await self._store.delete(refresh_token)
