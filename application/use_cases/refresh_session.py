from domain.errors import InvalidTokenError
from domain.auth.models import TokenPair
from ports.token_service_port import TokenServicePort


class RefreshSessionUseCase:
    # Exchanges a valid refresh token for a fresh token pair, rotating (and
    # invalidating) the old refresh token.
    def __init__(self, tokens: TokenServicePort):
        self._tokens = tokens

    async def execute(self, refresh_token: str) -> TokenPair:
        pair = await self._tokens.rotate(refresh_token)
        if pair is None:
            raise InvalidTokenError("invalid_refresh_token")
        return pair
