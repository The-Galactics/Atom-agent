"""End-to-end gRPC connection smoke test.

Starts the real ``AtomGrpcService`` on a loopback port and drives all RPCs
through generated client stubs over an insecure channel, matching Android's
``usePlaintext()`` development transport.

It avoids external dependencies by injecting fake use cases in the container,
so the test runs without provider keys or model downloads.
"""

import asyncio
import sys

import grpc
import pytest

import proto.atom_agent_pb2 as pb2
import proto.atom_agent_pb2_grpc as pb2_grpc
from application.dtos import (
    ChatOutputDTO,
    ExecuteCommandOutputDTO,
    SynthesizeSpeechOutputDTO,
    TranscribeAudioOutputDTO,
)
from infrastructure.grpc.server import AtomGrpcService
from infrastructure.grpc.error_interceptor import ErrorInterceptor


class _FakeChatUseCase:
    async def execute(self, input_dto):
        return ChatOutputDTO(
            text=f"Echo: {input_dto.text}",
            session_id=input_dto.session_id,
        )


class _FakeExecuteCommandUseCase:
    async def execute(self, input_dto):
        return ExecuteCommandOutputDTO(
            success=True,
            reply_text=f"Ack: {input_dto.text}",
            action_type="OPEN_APP",
            parameters={"app_name": "camera"},
            confidence=0.99,
            requires_confirmation=False,
        )


class _FakeTranscribeUseCase:
    def execute(self, input_dto):
        return TranscribeAudioOutputDTO(
            text="Transcripcion de prueba",
            language=input_dto.language or "es",
            duration_seconds=1.2,
            confidence=0.91,
            provider="fake_stt",
        )


class _FakeSynthesizeUseCase:
    async def execute(self, input_dto):
        return SynthesizeSpeechOutputDTO(
            audio_bytes=b"FAKEAUDIO",
            mime_type="audio/wav",
            format=input_dto.audio_format or "wav",
            duration_seconds=0.8,
            provider="fake_tts",
        )


class _FakeContainer:
    execute_command_use_case = _FakeExecuteCommandUseCase()
    chat_use_case = _FakeChatUseCase()
    transcribe_use_case = _FakeTranscribeUseCase()
    synthesize_use_case = _FakeSynthesizeUseCase()


class _FailingExecuteCommandUseCase:
    async def execute(self, _input_dto):
        raise RuntimeError("boom")


class _FailingChatUseCase:
    async def execute(self, _input_dto):
        raise RuntimeError("chat boom")


def _make_container(**overrides):
    container = _FakeContainer()
    for key, value in overrides.items():
        setattr(container, key, value)
    return container


async def _with_stub(container, callback):
    # Include the ErrorInterceptor so these tests exercise the real end-to-end
    # sanitization (US-10.1), matching how serve() wires the server.
    server = grpc.aio.server(interceptors=[ErrorInterceptor()])
    pb2_grpc.add_AtomAgentServiceServicer_to_server(AtomGrpcService(container), server)
    port = server.add_insecure_port("[::]:0")
    await server.start()

    try:
        async with grpc.aio.insecure_channel(f"localhost:{port}") as channel:
            stub = pb2_grpc.AtomAgentServiceStub(channel)
            return await callback(stub)
    finally:
        await server.stop(grace=None)


async def run() -> bool:
    server = grpc.aio.server()
    pb2_grpc.add_AtomAgentServiceServicer_to_server(
        AtomGrpcService(_FakeContainer()), server
    )
    port = server.add_insecure_port("[::]:0")
    await server.start()
    print(f"[server] AtomAgentService started on insecure port {port}")

    ok = True
    try:
        async with grpc.aio.insecure_channel(f"localhost:{port}") as channel:
            stub = pb2_grpc.AtomAgentServiceStub(channel)

            cmd = await stub.ExecuteCommand(
                pb2.CommandRequest(user_id="user_001", command="open camera")
            )
            print(
                f"[ExecuteCommand] success={cmd.success} "
                f"action={cmd.action_type} out_message={cmd.out_message!r}"
            )
            ok &= (
                cmd.success
                and cmd.action_type == "OPEN_APP"
                and cmd.out_message == "Ack: open camera"
                and cmd.parameters_json == '{"app_name": "camera"}'
            )

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

            transcription = await stub.Transcribe(
                pb2.TranscribeRequest(
                    audio_bytes=b"RIFFDATA",
                    mime_type="audio/wav",
                    language="es",
                    format="wav",
                    beam_size=5,
                )
            )
            print(
                f"[Transcribe] text={transcription.text!r} "
                f"language={transcription.language} provider={transcription.provider}"
            )
            ok &= (
                transcription.text == "Transcripcion de prueba"
                and transcription.language == "es"
                and transcription.provider == "fake_stt"
            )

            synth_chunks = []
            async for chunk in stub.Synthesize(
                pb2.SynthesizeRequest(
                    text="Hola",
                    voice="af_heart",
                    language="es",
                    format="wav",
                    speed=1.0,
                )
            ):
                synth_chunks.append(chunk)
                print(
                    f"[Synthesize] bytes={len(chunk.audio_bytes)} "
                    f"mime={chunk.mime_type!r} format={chunk.format!r}"
                )
            ok &= (
                len(synth_chunks) == 1
                and synth_chunks[0].audio_bytes == b"FAKEAUDIO"
                and synth_chunks[0].mime_type == "audio/wav"
            )
    finally:
        await server.stop(grace=None)

    print(f"\nRESULT: {'PASS' if ok else 'FAIL'}")
    return ok


def test_grpc_connection_full_flow():
    assert asyncio.run(run()) is True


def test_grpc_execute_command_unavailable_when_use_case_missing():
    async def _scenario(stub):
        with pytest.raises(grpc.aio.AioRpcError) as exc_info:
            await stub.ExecuteCommand(
                pb2.CommandRequest(user_id="user_001", command="open camera")
            )

        assert exc_info.value.code() == grpc.StatusCode.UNAVAILABLE
        details = exc_info.value.details()
        # Internal status must not leak; client sees a generic message.
        assert "intent stack offline" not in details
        assert "temporarily unavailable" in details

    container = _make_container(
        execute_command_use_case=None,
        intent_status="intent stack offline",
    )
    asyncio.run(_with_stub(container, _scenario))


def test_grpc_execute_command_internal_when_use_case_raises():
    async def _scenario(stub):
        with pytest.raises(grpc.aio.AioRpcError) as exc_info:
            await stub.ExecuteCommand(
                pb2.CommandRequest(user_id="user_001", command="open camera")
            )

        assert exc_info.value.code() == grpc.StatusCode.INTERNAL
        details = exc_info.value.details()
        # The raw exception text must never reach the client; only a generic
        # message plus a correlation request_id.
        assert "boom" not in details
        assert "Internal server error occurred" in details
        assert "request_id=" in details

    container = _make_container(execute_command_use_case=_FailingExecuteCommandUseCase())
    asyncio.run(_with_stub(container, _scenario))


def test_grpc_stream_chat_internal_when_use_case_raises():
    async def _scenario(stub):
        with pytest.raises(grpc.aio.AioRpcError) as exc_info:
            async for _chunk in stub.StreamChat(
                pb2.MessageRequest(user_id="user_001", chat_id="chat_001", message="hola")
            ):
                pass

        assert exc_info.value.code() == grpc.StatusCode.INTERNAL
        details = exc_info.value.details()
        assert "chat boom" not in details
        assert "Internal server error occurred" in details
        assert "request_id=" in details

    container = _make_container(chat_use_case=_FailingChatUseCase())
    asyncio.run(_with_stub(container, _scenario))


def test_grpc_stream_chat_unavailable_when_use_case_missing():
    async def _scenario(stub):
        with pytest.raises(grpc.aio.AioRpcError) as exc_info:
            async for _chunk in stub.StreamChat(
                pb2.MessageRequest(user_id="user_001", chat_id="chat_001", message="hola")
            ):
                pass

        assert exc_info.value.code() == grpc.StatusCode.UNAVAILABLE
        details = exc_info.value.details()
        assert "llm stack offline" not in details
        assert "temporarily unavailable" in details

    container = _make_container(chat_use_case=None, llm_status="llm stack offline")
    asyncio.run(_with_stub(container, _scenario))


def test_grpc_transcribe_unavailable_when_use_case_missing():
    async def _scenario(stub):
        with pytest.raises(grpc.aio.AioRpcError) as exc_info:
            await stub.Transcribe(
                pb2.TranscribeRequest(
                    audio_bytes=b"RIFFDATA",
                    mime_type="audio/wav",
                    language="es",
                    format="wav",
                    beam_size=5,
                )
            )

        assert exc_info.value.code() == grpc.StatusCode.UNAVAILABLE
        details = exc_info.value.details()
        assert "voice stack offline" not in details
        assert "temporarily unavailable" in details

    container = _make_container(transcribe_use_case=None, voice_status="voice stack offline")
    asyncio.run(_with_stub(container, _scenario))


def test_grpc_synthesize_unavailable_when_use_case_missing():
    async def _scenario(stub):
        with pytest.raises(grpc.aio.AioRpcError) as exc_info:
            async for _chunk in stub.Synthesize(
                pb2.SynthesizeRequest(
                    text="Hola",
                    voice="af_heart",
                    language="es",
                    format="wav",
                    speed=1.0,
                )
            ):
                pass

        assert exc_info.value.code() == grpc.StatusCode.UNAVAILABLE
        details = exc_info.value.details()
        assert "voice stack offline" not in details
        assert "temporarily unavailable" in details

    container = _make_container(synthesize_use_case=None, voice_status="voice stack offline")
    asyncio.run(_with_stub(container, _scenario))


if __name__ == "__main__":
    sys.exit(0 if asyncio.run(run()) else 1)
