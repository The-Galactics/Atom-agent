import grpc
from concurrent import futures
import proto.atom_agent_pb2 as pb2
import proto.atom_agent_pb2_grpc as pb2_grpc
from application.dtos import ChatInputDTO, TranscribeAudioInputDTO, SynthesizeSpeechInputDTO

class AtomGrpcService(pb2_grpc.AtomAgentServiceServicer):
    def __init__(self, container):
        self.container = container

    async def ExecuteCommand(self, request, context):

        # Placeholder for command execution logic
        return pb2.CommandResponse(
            success=True, 
            out_message=f"Agent acknowledged command: {request.command}"
        )

    async def StreamChat(self, request, context):

        input_dto = ChatInputDTO(text=request.message, session_id=request.user_id)
        output = await self.container.chat_use_case.execute(input_dto)
        
        yield pb2.MessageResponse(
            script_token=output.text, 
            status="success", 
            finished=True
        )

    async def Transcribe(self, request, context):
        """Implementation of Transcribe unary call."""
        input_dto = TranscribeAudioInputDTO(
            audio_bytes=request.audio_bytes,
            mime_type=request.mime_type,
            language=request.language,
            file_format=request.format,
            beam_size=request.beam_size
        )
        # Note:STT execution is synchronous in current implementation
        output = self.container.transcribe_use_case.execute(input_dto)

        return pb2.TranscribeResponse(
            text=output.text,
            language=output.language,
            duration_seconds=output.duration_seconds or 0.0,
            confidence=output.confidence or 0.0,
            provider=output.provider
        )

    async def Synthesize(self, request, context):

        input_dto = SynthesizeSpeechInputDTO(
            text=request.text,
            voice=request.voice,
            language=request.language,
            audio_format=request.format,
            speed=request.speed
        )
        # Note: TTS execution is synchronous in current implementation
        output = self.container.synthesize_use_case.execute(input_dto)

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
