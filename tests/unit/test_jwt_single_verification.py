"""US-10.2: the access token is verified exactly once per request (by the
AuthInterceptor); protected handlers read the resulting Principal from the call
context without re-checking the signature."""

import asyncio

import grpc

from domain.auth.models import Principal
from infrastructure.grpc.auth_interceptor import AuthInterceptor, principal_from_context

PROTECTED = "/com.atom.proto.AtomAgentService/ExecuteCommand"


class CountingTokens:
    def __init__(self):
        self.calls = 0

    def verify_access(self, token):
        self.calls += 1
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


def _make_handler(tokens, behavior):
    async def continuation(_hcd):
        return grpc.unary_unary_rpc_method_handler(behavior)

    return asyncio.run(
        AuthInterceptor(tokens).intercept_service(continuation, HandlerCallDetails(PROTECTED))
    )


def test_token_verified_once_and_principal_available_to_handler():
    tokens = CountingTokens()
    captured = {}

    async def behavior(request, context):
        captured["principal"] = principal_from_context()
        return "OK"

    handler = _make_handler(tokens, behavior)
    ctx = FakeContext(metadata=(("authorization", "Bearer good"),))

    assert asyncio.run(handler.unary_unary("req", ctx)) == "OK"
    assert captured["principal"].user_id == "u1"
    # Exactly one signature verification for the whole request — no redundant
    # re-verify inside the handler.
    assert tokens.calls == 1


def test_principal_is_none_without_interceptor():
    # Called outside any authorized RPC (e.g. auth disabled / direct handler call):
    # there is no verified principal, so handlers fall back to their own default.
    assert principal_from_context() is None
