import asyncio

import pytest

from application.use_cases.register_user import RegisterUserUseCase
from application.use_cases.authenticate_user import AuthenticateUserUseCase
from application.use_cases.authenticate_with_google import AuthenticateWithGoogleUseCase
from application.use_cases.refresh_session import RefreshSessionUseCase
from domain.auth.models import GoogleIdentity, TokenPair
from domain.errors import (
    AuthenticationError,
    DomainValidationError,
    InvalidTokenError,
    UserAlreadyExistsError,
)
from domain.user.models import User
from ports.user_repository_port import UserRepositoryPort
from ports.password_hasher_port import PasswordHasherPort
from ports.token_service_port import TokenServicePort
from ports.google_id_token_verifier_port import GoogleIdTokenVerifierPort


# --- Fakes -----------------------------------------------------------------

class FakeUserRepository(UserRepositoryPort):
    def __init__(self):
        self.by_id: dict[str, User] = {}
        self.password_updated = False

    async def find_by_email(self, email):
        return next((u for u in self.by_id.values() if u.email == email), None)

    async def find_by_id(self, user_id):
        return self.by_id.get(user_id)

    async def find_by_google_sub(self, google_sub):
        return next((u for u in self.by_id.values()
                     if u.google_sub == google_sub), None)

    async def save(self, user):
        if any(u.email == user.email for u in self.by_id.values()):
            raise UserAlreadyExistsError()
        self.by_id[user.id] = user
        return user

    async def update_password_hash(self, user_id, password_hash):
        self.by_id[user_id].password_hash = password_hash
        self.password_updated = True

    async def update_settings(self, user_id, settings):
        self.by_id[user_id].settings = settings
        return self.by_id[user_id]

    async def link_google(self, user_id, google_sub):
        user = self.by_id[user_id]
        user.google_sub = google_sub
        if "google" not in user.auth_providers:
            user.auth_providers.append("google")
        return user


class FakeHasher(PasswordHasherPort):
    def __init__(self, rehash: bool = False):
        self._rehash = rehash

    def hash(self, raw_password):
        return "hash:" + raw_password

    def verify(self, raw_password, encoded):
        return encoded == "hash:" + raw_password

    def needs_rehash(self, encoded):
        return self._rehash


class FakeTokenService(TokenServicePort):
    def __init__(self):
        self.refresh_db: dict[str, str] = {}
        self._n = 0

    async def issue_pair(self, user_id, email=None):
        self._n += 1
        refresh = f"refresh-{user_id}-{self._n}"
        self.refresh_db[refresh] = user_id
        return TokenPair(access_token=f"access-{user_id}",
                         refresh_token=refresh, expires_in=900, user_id=user_id)

    def verify_access(self, access_token):
        return None

    async def rotate(self, refresh_token):
        user_id = self.refresh_db.pop(refresh_token, None)
        if user_id is None:
            return None
        return await self.issue_pair(user_id)

    async def revoke(self, refresh_token):
        self.refresh_db.pop(refresh_token, None)


class FakeGoogleVerifier(GoogleIdTokenVerifierPort):
    def __init__(self, identity=None, error=None):
        self._identity = identity
        self._error = error

    def verify(self, raw_id_token):
        if self._error is not None:
            raise self._error
        return self._identity


def _register_uc(users=None):
    users = users or FakeUserRepository()
    return RegisterUserUseCase(users, FakeHasher(), FakeTokenService()), users


# --- Register --------------------------------------------------------------

def test_register_success_stores_hash_not_plaintext():
    uc, users = _register_uc()
    pair = asyncio.run(uc.execute("User@Example.com", "secret123", "Carlos"))

    assert isinstance(pair, TokenPair)
    user = asyncio.run(users.find_by_email("user@example.com"))  # normalized
    assert user is not None
    assert user.password_hash == "hash:secret123"
    assert "secret123" != user.password_hash
    assert user.auth_providers == ["password"]


def test_register_duplicate_email_rejected():
    uc, users = _register_uc()
    asyncio.run(uc.execute("a@b.com", "secret123"))
    with pytest.raises(UserAlreadyExistsError):
        asyncio.run(uc.execute("a@b.com", "another123"))


def test_register_weak_password_rejected():
    uc, _ = _register_uc()
    with pytest.raises(DomainValidationError):
        asyncio.run(uc.execute("a@b.com", "short"))          # too short
    with pytest.raises(DomainValidationError):
        asyncio.run(uc.execute("a@b.com", "alllettersonly"))  # no digit


def test_register_invalid_email_rejected():
    uc, _ = _register_uc()
    with pytest.raises(DomainValidationError):
        asyncio.run(uc.execute("not-an-email", "secret123"))


# --- Login -----------------------------------------------------------------

def test_login_success():
    users = FakeUserRepository()
    asyncio.run(users.save(User.new("a@b.com", "hash:secret123")))
    uc = AuthenticateUserUseCase(users, FakeHasher(), FakeTokenService())

    pair = asyncio.run(uc.execute("A@B.com", "secret123"))
    assert pair.user_id is not None


def test_login_wrong_password_and_unknown_user_fail_identically():
    users = FakeUserRepository()
    asyncio.run(users.save(User.new("a@b.com", "hash:secret123")))
    uc = AuthenticateUserUseCase(users, FakeHasher(), FakeTokenService())

    with pytest.raises(AuthenticationError):
        asyncio.run(uc.execute("a@b.com", "wrongpass1"))
    with pytest.raises(AuthenticationError):
        asyncio.run(uc.execute("nobody@b.com", "whatever1"))


def test_login_google_only_account_rejects_password():
    users = FakeUserRepository()
    asyncio.run(users.save(User.federated("g@b.com", google_sub="sub-1")))
    uc = AuthenticateUserUseCase(users, FakeHasher(), FakeTokenService())

    with pytest.raises(AuthenticationError):
        asyncio.run(uc.execute("g@b.com", "anything1"))


def test_login_triggers_rehash_when_needed():
    users = FakeUserRepository()
    asyncio.run(users.save(User.new("a@b.com", "hash:secret123")))
    uc = AuthenticateUserUseCase(users, FakeHasher(rehash=True), FakeTokenService())

    asyncio.run(uc.execute("a@b.com", "secret123"))
    assert users.password_updated is True


# --- Google ----------------------------------------------------------------

def test_google_provisions_new_federated_user():
    users = FakeUserRepository()
    verifier = FakeGoogleVerifier(GoogleIdentity(sub="sub-1", email="g@b.com", name="G"))
    uc = AuthenticateWithGoogleUseCase(users, verifier, FakeTokenService())

    pair = asyncio.run(uc.execute("fake-id-token"))
    user = asyncio.run(users.find_by_google_sub("sub-1"))
    assert pair.user_id == user.id
    assert user.password_hash is None
    assert user.auth_providers == ["google"]


def test_google_links_existing_email_account():
    users = FakeUserRepository()
    existing = asyncio.run(users.save(User.new("g@b.com", "hash:secret123")))
    verifier = FakeGoogleVerifier(GoogleIdentity(sub="sub-1", email="g@b.com"))
    uc = AuthenticateWithGoogleUseCase(users, verifier, FakeTokenService())

    asyncio.run(uc.execute("fake-id-token"))
    linked = asyncio.run(users.find_by_id(existing.id))
    assert linked.google_sub == "sub-1"
    assert "google" in linked.auth_providers
    # No duplicate account created.
    assert len(users.by_id) == 1


def test_google_existing_sub_returns_same_user():
    users = FakeUserRepository()
    asyncio.run(users.save(User.federated("g@b.com", google_sub="sub-1")))
    verifier = FakeGoogleVerifier(GoogleIdentity(sub="sub-1", email="g@b.com"))
    uc = AuthenticateWithGoogleUseCase(users, verifier, FakeTokenService())

    asyncio.run(uc.execute("fake-id-token"))
    assert len(users.by_id) == 1


def test_google_rejects_invalid_token():
    users = FakeUserRepository()
    verifier = FakeGoogleVerifier(error=AuthenticationError("email_not_verified"))
    uc = AuthenticateWithGoogleUseCase(users, verifier, FakeTokenService())

    with pytest.raises(AuthenticationError):
        asyncio.run(uc.execute("bad-token"))


# --- Refresh ---------------------------------------------------------------

def test_refresh_rotates_token():
    tokens = FakeTokenService()
    issued = asyncio.run(tokens.issue_pair("user-1"))
    uc = RefreshSessionUseCase(tokens)

    rotated = asyncio.run(uc.execute(issued.refresh_token))
    assert rotated.refresh_token != issued.refresh_token
    # Old refresh token is now invalid.
    with pytest.raises(InvalidTokenError):
        asyncio.run(uc.execute(issued.refresh_token))


def test_refresh_invalid_token_rejected():
    uc = RefreshSessionUseCase(FakeTokenService())
    with pytest.raises(InvalidTokenError):
        asyncio.run(uc.execute("nonexistent"))
