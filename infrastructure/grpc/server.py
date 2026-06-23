import json
import logging

import grpc
from concurrent import futures
import proto.atom_agent_pb2 as pb2
import proto.atom_agent_pb2_grpc as pb2_grpc
from application.dtos import (
    ChatInputDTO,
    ExecuteCommandInputDTO,
    TranscribeAudioInputDTO,
    SynthesizeSpeechInputDTO,
)

logger = logging.getLogger("voice_module")

class AtomGrpcService(pb2_grpc.AtomAgentServiceServicer):
    def __init__(self, container):
        self.container = container

    async def ExecuteCommand(self, request, context):

        logger.info(
            "grpc_ExecuteCommand peer=%s user_id=%s command=%r",
            context.peer(), request.user_id, request.command,
        )
        use_case = self.container.execute_command_use_case
        if use_case is None:
            detail = getattr(self.container, "intent_status", "intent provider unavailable")
            await context.abort(
                grpc.StatusCode.UNAVAILABLE,
                f"Intent provider unavailable: {detail}",
            )
            return

        try:
            input_dto = ExecuteCommandInputDTO(text=request.command, user_id=request.user_id)
            output = await use_case.execute(input_dto)
        except Exception as exc:
            logger.exception("grpc_ExecuteCommand failed peer=%s", context.peer())
            await context.abort(grpc.StatusCode.INTERNAL, f"command failed: {exc}")
            return

        logger.info(
            "grpc_ExecuteCommand ok peer=%s action=%s confidence=%.2f",
            context.peer(), output.action_type, output.confidence,
        )
        return pb2.CommandResponse(
            success=output.success,
            out_message=output.reply_text,
            action_type=output.action_type,
            parameters_json=json.dumps(output.parameters, ensure_ascii=False),
            confidence=output.confidence,
            requires_confirmation=output.requires_confirmation,
        )

    async def StreamChat(self, request, context):

        logger.info(
            "grpc_StreamChat peer=%s user_id=%s message=%r",
            context.peer(), request.user_id, request.message,
        )
        use_case = self.container.chat_use_case
        if use_case is None:
            logger.warning("grpc_StreamChat unavailable peer=%s", context.peer())
            await context.abort(
                grpc.StatusCode.UNAVAILABLE,
                f"LLM provider unavailable: {self.container.llm_status}",
            )
            return
        try:
            input_dto = ChatInputDTO(text=request.message, session_id=request.user_id)
            output = await use_case.execute(input_dto)
        except Exception as exc:
            logger.exception("grpc_StreamChat failed peer=%s", context.peer())
            await context.abort(grpc.StatusCode.INTERNAL, f"chat failed: {exc}")
            return

        logger.info("grpc_StreamChat ok peer=%s chars=%d", context.peer(), len(output.text))
        yield pb2.MessageResponse(
            script_token=output.text,
            status="success",
            finished=True
        )

    async def Transcribe(self, request, context):
        """Implementation of Transcribe unary call."""
        use_case = self.container.transcribe_use_case
        if use_case is None:
            detail = getattr(self.container, "voice_status", "voice provider unavailable")
            await context.abort(
                grpc.StatusCode.UNAVAILABLE,
                f"Voice provider unavailable (STT): {detail}",
            )
            return

        input_dto = TranscribeAudioInputDTO(
            audio_bytes=request.audio_bytes,
            mime_type=request.mime_type,
            language=request.language,
            file_format=request.format,
            beam_size=request.beam_size
        )
        # Note:STT execution is synchronous in current implementation
        output = use_case.execute(input_dto)

        return pb2.TranscribeResponse(
            text=output.text,
            language=output.language,
            duration_seconds=output.duration_seconds or 0.0,
            confidence=output.confidence or 0.0,
            provider=output.provider
        )

    async def Synthesize(self, request, context):
        use_case = self.container.synthesize_use_case
        if use_case is None:
            detail = getattr(self.container, "voice_status", "voice provider unavailable")
            await context.abort(
                grpc.StatusCode.UNAVAILABLE,
                f"Voice provider unavailable (TTS): {detail}",
            )
            return

        input_dto = SynthesizeSpeechInputDTO(
            text=request.text,
            voice=request.voice,
            language=request.language,
            audio_format=request.format,
            speed=request.speed
        )
        output = await use_case.execute(input_dto)

        yield pb2.SynthesizeResponse(
            audio_bytes=output.audio_bytes,
            mime_type=output.mime_type,
            format=output.format
        )

async def serve(container, port: int = 50051):
    
    server = grpc.aio.server()
    pb2_grpc.add_AtomAgentServiceServicer_to_server(AtomGrpcService(container), server)
    server.add_insecure_port(f'[::]:{port}')
    print(f"gRPC Server started on port {port}")
    await server.start()
    await server.wait_for_termination()
