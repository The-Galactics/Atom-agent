import asyncio

import grpc
import pytest

from infrastructure.grpc.auth_interceptor import AuthInterceptor
from domain.auth.models import Principal

PUBLIC = "/com.atom.proto.AtomAgentService/Login"
PROTECTED = "/com.atom.proto.AtomAgentService/ExecuteCommand"


class FakeTokens:
    def verify_access(self, token):
        return Principal(user_id="u1") if token == "good" else None


class HandlerCallDetails:
    def __init__(self, method):
        self.method = method
        self.invocation_metadata = ()


class _Abort(Exception):
    pass


class FakeContext:
    def __init__(self, metadata=()):
        self._md = metadata

    def invocation_metadata(self):
        return self._md

    async def abort(self, code, details):
        raise _Abort(str(code))


async def _behavior(request, context):
    return "OK"


async def _continuation(_hcd):
    return grpc.unary_unary_rpc_method_handler(_behavior)


def _intercept(interceptor, method):
    return asyncio.run(interceptor.intercept_service(_continuation, HandlerCallDetails(method)))


def test_public_method_passes_through():
    handler = _intercept(AuthInterceptor(FakeTokens()), PUBLIC)
    assert asyncio.run(handler.unary_unary("req", FakeContext())) == "OK"


def test_auth_disabled_passes_through():
    handler = _intercept(AuthInterceptor(None), PROTECTED)
    assert asyncio.run(handler.unary_unary("req", FakeContext())) == "OK"


def test_protected_without_token_aborts():
    handler = _intercept(AuthInterceptor(FakeTokens()), PROTECTED)
    with pytest.raises(_Abort):
        asyncio.run(handler.unary_unary("req", FakeContext()))


def test_protected_with_invalid_token_aborts():
    handler = _intercept(AuthInterceptor(FakeTokens()), PROTECTED)
    ctx = FakeContext(metadata=(("authorization", "Bearer bad"),))
    with pytest.raises(_Abort):
        asyncio.run(handler.unary_unary("req", ctx))


def test_protected_with_valid_token_passes():
    handler = _intercept(AuthInterceptor(FakeTokens()), PROTECTED)
    ctx = FakeContext(metadata=(("authorization", "Bearer good"),))
    assert asyncio.run(handler.unary_unary("req", ctx)) == "OK"
