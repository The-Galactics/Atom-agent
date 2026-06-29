import re

from domain.errors import DomainValidationError, UserAlreadyExistsError
from domain.user.models import User
from domain.auth.models import TokenPair
from ports.user_repository_port import UserRepositoryPort
from ports.password_hasher_port import PasswordHasherPort
from ports.token_service_port import TokenServicePort

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_MIN_PASSWORD_LEN = 8


def _validate_email(email: str) -> None:
    if not _EMAIL_RE.match(email):
        raise DomainValidationError("invalid_email")


def _validate_password_strength(password: str) -> None:
    # Length + character-class check ONLY. The password must NOT go through an
    # injection regex: a strong password legitimately contains ' ; -- etc.
    if len(password) < _MIN_PASSWORD_LEN:
        raise DomainValidationError("weak_password")
    if not any(c.isalpha() for c in password) or not any(c.isdigit() for c in password):
        raise DomainValidationError("weak_password")


class RegisterUserUseCase:
    # Registers an email/password account and returns a session token pair
    # (registration auto-logs the user in).
    def __init__(self, users: UserRepositoryPort, hasher: PasswordHasherPort,
                 tokens: TokenServicePort):
        self._users = users
        self._hasher = hasher
        self._tokens = tokens

    async def execute(self, email: str, password: str,
                      display_name: str | None = None) -> TokenPair:
        norm = email.strip().lower()
        _validate_email(norm)
        _validate_password_strength(password)
        if await self._users.find_by_email(norm) is not None:
            raise UserAlreadyExistsError()
        user = User.new(
            email=norm,
            password_hash=self._hasher.hash(password),
            display_name=display_name,
        )
        saved = await self._users.save(user)
        return await self._tokens.issue_pair(user_id=saved.id, email=saved.email)
