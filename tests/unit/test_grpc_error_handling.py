import asyncio

import grpc
import pytest

import proto.atom_agent_pb2 as pb2
from infrastructure.grpc.server import AtomGrpcService


class _Abort(Exception):
    def __init__(self, code, details):
        self.code = code
        self.details = details


class FakeContext:
    async def abort(self, code, details):
        raise _Abort(code, details)

    def invocation_metadata(self):
        return ()

    def peer(self):
        return "test-peer"


class _Boom:
    async def execute(self, _dto):
        raise RuntimeError("secret db dsn leaked")


class _Container:
    def __init__(self, *, execute_command_use_case, intent_status="ready"):
        self.execute_command_use_case = execute_command_use_case
        self.intent_status = intent_status
        self.token_service = None


def _run(coro):
    return asyncio.run(coro)


def test_execute_command_unavailable_does_not_leak_internal_status():
    svc = AtomGrpcService(
        _Container(execute_command_use_case=None, intent_status="SECRET_BACKEND_STATE")
    )
    with pytest.raises(_Abort) as ei:
        _run(svc.ExecuteCommand(pb2.CommandRequest(command="hi"), FakeContext()))
    assert ei.value.code == grpc.StatusCode.UNAVAILABLE
    # The internal status string must not reach the client.
    assert "SECRET_BACKEND_STATE" not in ei.value.details


def test_execute_command_propagates_raw_exception_to_interceptor():
    # The handler must NOT swallow + echo str(exc); it lets the exception reach
    # the global ErrorInterceptor, which sanitizes it into a generic INTERNAL.
    svc = AtomGrpcService(_Container(execute_command_use_case=_Boom()))
    with pytest.raises(RuntimeError):
        _run(svc.ExecuteCommand(pb2.CommandRequest(command="hi"), FakeContext()))


class _BoomChat:
    async def execute(self, _dto):
        raise RuntimeError("secret chat boom")


class _ChatContainer:
    def __init__(self, *, chat_use_case, llm_status="ready"):
        self.chat_use_case = chat_use_case
        self.llm_status = llm_status
        self.token_service = None


def _drain_stream(async_gen):
    async def _run_drain():
        async for _ in async_gen:
            pass
    return _run(_run_drain())


def test_stream_chat_unavailable_does_not_leak_internal_status():
    svc = AtomGrpcService(_ChatContainer(chat_use_case=None, llm_status="SECRET_LLM_STATE"))
    with pytest.raises(_Abort) as ei:
        _drain_stream(svc.StreamChat(pb2.MessageRequest(message="hi"), FakeContext()))
    assert ei.value.code == grpc.StatusCode.UNAVAILABLE
    assert "SECRET_LLM_STATE" not in ei.value.details


def test_stream_chat_propagates_raw_exception_to_interceptor():
    svc = AtomGrpcService(_ChatContainer(chat_use_case=_BoomChat()))
    with pytest.raises(RuntimeError):
        _drain_stream(svc.StreamChat(pb2.MessageRequest(message="hi"), FakeContext()))
