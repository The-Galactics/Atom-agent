import asyncio
import logging
from unittest.mock import AsyncMock
import proto.atom_agent_pb2 as pb2
# Real class is AtomGrpcService (not AtomAgentService as the brief template assumed)
from infrastructure.grpc.server import AtomGrpcService


class _FakeContext:
    def peer(self):
        return "test"

    async def abort(self, code, details):
        raise AssertionError(f"aborted: {code} {details}")


class _Container:
    def __init__(self, chat_use_case):
        self.chat_use_case = chat_use_case
        self.user_repository = None


def test_streamchat_emits_total_latency_span(caplog):
    out = type("O", (), {"text": "hi"})()
    uc = AsyncMock()
    uc.execute.return_value = out
    svc = AtomGrpcService(_Container(uc))
    req = pb2.MessageRequest(message="hello", chat_id="c1")

    async def drain():
        return [m async for m in svc.StreamChat(req, _FakeContext())]

    with caplog.at_level(logging.INFO, logger="atom.latency"):
        asyncio.run(drain())

    assert any(
        "label=StreamChat.total" in r.getMessage()
        for r in caplog.records if r.name == "atom.latency"
    )
