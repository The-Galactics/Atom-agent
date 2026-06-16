"""End-to-end gRPC connection smoke test.

Starts the real ``AtomGrpcService`` (the same servicer wired in
``infrastructure/grpc/server.py``) on a loopback port and drives it with the
generated client stubs over an insecure channel -- mirroring the Android
client's ``usePlaintext()`` transport.

It avoids external dependencies (NVIDIA / Qdrant / Kokoro) by injecting a stub
container whose ``chat_use_case`` returns a canned answer, so ``StreamChat`` can
be exercised without any API keys.

This is written as a plain ``asyncio`` runner rather than a ``pytest.mark.asyncio``
test because the project does not currently depend on ``pytest-asyncio``. Run it
directly:

    PYTHONPATH=. .venv/bin/python tests/integration/test_grpc_connection.py
"""

import asyncio
import sys

import grpc

import proto.atom_agent_pb2 as pb2
import proto.atom_agent_pb2_grpc as pb2_grpc
from application.dtos import ChatOutputDTO
from infrastructure.grpc.server import AtomGrpcService


class _FakeChatUseCase:
    async def execute(self, input_dto):
        return ChatOutputDTO(
            text=f"Echo: {input_dto.text}",
            session_id=input_dto.session_id,
        )


class _FakeContainer:
    chat_use_case = _FakeChatUseCase()


async def run() -> bool:
    server = grpc.aio.server()
    pb2_grpc.add_AtomAgentServiceServicer_to_server(
        AtomGrpcService(_FakeContainer()), server
    )
    port = server.add_insecure_port("[::]:0")
    await server.start()
    print(f"[server] AtomAgentService started on insecure port {port}")

    ok = True
    async with grpc.aio.insecure_channel(f"localhost:{port}") as channel:
        stub = pb2_grpc.AtomAgentServiceStub(channel)

        # 1) ExecuteCommand (unary, pure placeholder, no external deps).
        cmd = await stub.ExecuteCommand(
            pb2.CommandRequest(user_id="user_001", command="open camera")
        )
        print(f"[ExecuteCommand] success={cmd.success} out_message={cmd.out_message!r}")
        ok &= cmd.success and cmd.out_message == "Agent acknowledged command: open camera"

        # 2) StreamChat (server-streaming, real server code + fake chat_use_case).
        tokens, last_finished = [], None
        async for chunk in stub.StreamChat(
            pb2.MessageRequest(
                user_id="user_001",
                chat_id="chat_001",
                message="Hello Atom, can you help me?",
            )
        ):
            tokens.append(chunk.script_token)
            last_finished = chunk.finished
            print(
                f"[StreamChat] token={chunk.script_token!r} "
                f"status={chunk.status!r} finished={chunk.finished}"
            )
        ok &= "".join(tokens) == "Echo: Hello Atom, can you help me?" and last_finished is True

    await server.stop(grace=None)
    print(f"\nRESULT: {'PASS' if ok else 'FAIL'}")
    return ok


if __name__ == "__main__":
    sys.exit(0 if asyncio.run(run()) else 1)
