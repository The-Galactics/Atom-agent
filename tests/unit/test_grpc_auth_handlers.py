import asyncio

import grpc
import pytest
from mongomock_motor import AsyncMongoMockClient

import proto.atom_agent_pb2 as pb2
from infrastructure.grpc.server import AtomGrpcService
from adapters.user_store.mongo_user_repository import MongoUserRepository
from adapters.security.argon2_password_hasher import Argon2PasswordHasher
from adapters.security.jwt_token_service import JwtTokenService
from adapters.security.in_memory_refresh_token_store import InMemoryRefreshTokenStore
from application.use_cases.register_user import RegisterUserUseCase
from application.use_cases.authenticate_user import AuthenticateUserUseCase
from application.use_cases.refresh_session import RefreshSessionUseCase


class _Abort(Exception):
    def __init__(self, code, details):
        self.code = code
        self.details = details


class FakeContext:
    async def abort(self, code, details):
        raise _Abort(code, details)

    def invocation_metadata(self):
        return ()


class _Container:
    """Minimal container exposing only the auth fields the handlers read."""
    def __init__(self):
        users = MongoUserRepository(AsyncMongoMockClient(), "test")
        hasher = Argon2PasswordHasher(time_cost=1, memory_cost=512, parallelism=1)  # fast
        tokens = JwtTokenService(InMemoryRefreshTokenStore(), signing_key="x" * 32)
        self.token_service = tokens
        self.register_use_case = RegisterUserUseCase(users, hasher, tokens)
        self.authenticate_use_case = AuthenticateUserUseCase(users, hasher, tokens)
        self.refresh_session_use_case = RefreshSessionUseCase(tokens)
        self.authenticate_with_google_use_case = None
        self.auth_status = "ready"


def _service():
    return AtomGrpcService(_Container())


def _run(coro):
    return asyncio.run(coro)


def test_register_returns_tokens():
    svc = _service()
    resp = _run(svc.Register(
        pb2.RegisterRequest(email="a@b.com", password="secret123", display_name="C"),
        FakeContext()))
    assert resp.access_token and resp.refresh_token and resp.user_id


def test_register_duplicate_already_exists():
    svc = _service()
    _run(svc.Register(pb2.RegisterRequest(email="a@b.com", password="secret123"), FakeContext()))
    with pytest.raises(_Abort) as ei:
        _run(svc.Register(pb2.RegisterRequest(email="a@b.com", password="secret123"), FakeContext()))
    assert ei.value.code == grpc.StatusCode.ALREADY_EXISTS


def test_register_invalid_password_argument():
    svc = _service()
    with pytest.raises(_Abort) as ei:
        _run(svc.Register(pb2.RegisterRequest(email="a@b.com", password="short"), FakeContext()))
    assert ei.value.code == grpc.StatusCode.INVALID_ARGUMENT


def test_login_success_and_wrong_password():
    svc = _service()
    _run(svc.Register(pb2.RegisterRequest(email="a@b.com", password="secret123"), FakeContext()))
    ok = _run(svc.Login(pb2.LoginRequest(email="a@b.com", password="secret123"), FakeContext()))
    assert ok.access_token
    with pytest.raises(_Abort) as ei:
        _run(svc.Login(pb2.LoginRequest(email="a@b.com", password="wrongpass1"), FakeContext()))
    assert ei.value.code == grpc.StatusCode.UNAUTHENTICATED


def test_refresh_rotates_and_invalidates_old():
    svc = _service()
    reg = _run(svc.Register(pb2.RegisterRequest(email="a@b.com", password="secret123"), FakeContext()))
    new = _run(svc.RefreshToken(pb2.RefreshRequest(refresh_token=reg.refresh_token), FakeContext()))
    assert new.refresh_token != reg.refresh_token
    with pytest.raises(_Abort) as ei:
        _run(svc.RefreshToken(pb2.RefreshRequest(refresh_token=reg.refresh_token), FakeContext()))
    assert ei.value.code == grpc.StatusCode.UNAUTHENTICATED


def test_google_unavailable_when_not_configured():
    svc = _service()  # authenticate_with_google_use_case is None
    with pytest.raises(_Abort) as ei:
        _run(svc.AuthenticateWithGoogle(pb2.GoogleAuthRequest(id_token="x"), FakeContext()))
    assert ei.value.code == grpc.StatusCode.UNAVAILABLE
