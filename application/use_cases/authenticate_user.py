from domain.errors import AuthenticationError
from domain.auth.models import TokenPair
from ports.user_repository_port import UserRepositoryPort
from ports.password_hasher_port import PasswordHasherPort
from ports.token_service_port import TokenServicePort


class AuthenticateUserUseCase:
    # Validates email/password credentials and issues a session token pair.
    def __init__(self, users: UserRepositoryPort, hasher: PasswordHasherPort,
                 tokens: TokenServicePort):
        self._users = users
        self._hasher = hasher
        self._tokens = tokens

    async def execute(self, email: str, password: str) -> TokenPair:
        user = await self._users.find_by_email(email.strip().lower())
        # Identical generic failure for "no such user", "google-only account" and
        # "wrong password" — never reveal which, to prevent account enumeration.
        if (user is None
                or user.password_hash is None
                or not self._hasher.verify(password, user.password_hash)):
            raise AuthenticationError("invalid_credentials")
        # Opportunistically upgrade the hash if the cost parameters have increased.
        if self._hasher.needs_rehash(user.password_hash):
            await self._users.update_password_hash(user.id, self._hasher.hash(password))
        return await self._tokens.issue_pair(user_id=user.id, email=user.email)
