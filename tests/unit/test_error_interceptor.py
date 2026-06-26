import asyncio
import logging

import grpc
import pytest

from infrastructure.grpc.error_interceptor import ErrorInterceptor

METHOD = "/com.atom.proto.AtomAgentService/ExecuteCommand"


class HandlerCallDetails:
    def __init__(self, method):
        self.method = method
        self.invocation_metadata = ()


class FakeContext:
    """Mirrors grpc.aio ServicerContext: abort records the status and raises
    AbortError (as real grpc.aio does to unwind the RPC)."""

    def __init__(self):
        self.aborted_code = None
        self.aborted_details = None

    def invocation_metadata(self):
        return ()

    async def abort(self, code, details):
        self.aborted_code = code
        self.aborted_details = details
        raise grpc.aio.AbortError(str(code))


def _wrap(behavior):
    async def _continuation(_hcd):
        return grpc.unary_unary_rpc_method_handler(behavior)
    return asyncio.run(
        ErrorInterceptor().intercept_service(_continuation, HandlerCallDetails(METHOD))
    )


def test_raw_exception_becomes_internal_without_exc_text(caplog):
    async def boom(request, context):
        raise RuntimeError("secret db dsn leaked")

    handler = _wrap(boom)
    ctx = FakeContext()
    with caplog.at_level(logging.ERROR):
        with pytest.raises(grpc.aio.AbortError):
            asyncio.run(handler.unary_unary("req", ctx))

    assert ctx.aborted_code == grpc.StatusCode.INTERNAL
    # The client-facing detail must never echo the internal exception text.
    assert "secret db dsn leaked" not in (ctx.aborted_details or "")
    # The real cause is recorded server-side for ops.
    assert "secret db dsn leaked" in caplog.text


def test_request_id_correlates_client_detail_and_log(caplog):
    async def boom(request, context):
        raise RuntimeError("boom")

    handler = _wrap(boom)
    ctx = FakeContext()
    with caplog.at_level(logging.ERROR):
        with pytest.raises(grpc.aio.AbortError):
            asyncio.run(handler.unary_unary("req", ctx))

    assert "request_id=" in ctx.aborted_details
    request_id = ctx.aborted_details.split("request_id=")[1].rstrip(")")
    assert request_id in caplog.text


def test_deliberate_abort_is_not_overwritten():
    async def deliberate(request, context):
        await context.abort(grpc.StatusCode.UNAVAILABLE, "service down")

    handler = _wrap(deliberate)
    ctx = FakeContext()
    with pytest.raises(grpc.aio.AbortError):
        asyncio.run(handler.unary_unary("req", ctx))

    # A handler's intentional abort keeps its own code/detail — not turned into INTERNAL.
    assert ctx.aborted_code == grpc.StatusCode.UNAVAILABLE
    assert ctx.aborted_details == "service down"
