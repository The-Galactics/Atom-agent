from typing import Callable
from fastapi import APIRouter, File, Form, HTTPException, Response, UploadFile
from pydantic import ValidationError
from application.dtos import TranscribeAudioInputDTO, SynthesizeSpeechInputDTO
from application.use_cases.transcribe_audio import TranscribeAudioUseCase
from application.use_cases.synthesize_speech import SynthesizeSpeechUseCase
from api.schemas import SynthesizeRequest, TranscribeResponse
from domain.errors import DomainError, DomainValidationError


UseCaseProvider = Callable[[], TranscribeAudioUseCase] | TranscribeAudioUseCase
UseCaseProviderTts = Callable[[], SynthesizeSpeechUseCase] | SynthesizeSpeechUseCase


def create_voice_router(
    transcribe_use_case_provider: UseCaseProvider,
    synthesize_use_case_provider: UseCaseProviderTts,
) -> APIRouter:
    router = APIRouter(prefix="/voice", tags=["voice"])

    def _resolve_transcribe_use_case() -> TranscribeAudioUseCase:
        return transcribe_use_case_provider() if callable(transcribe_use_case_provider) else transcribe_use_case_provider

    def _resolve_synthesize_use_case() -> SynthesizeSpeechUseCase:
        return synthesize_use_case_provider() if callable(synthesize_use_case_provider) else synthesize_use_case_provider

    @router.post("/transcribe", response_model=TranscribeResponse)
    async def transcribe(
        audio_file: UploadFile = File(...),
        language: str | None = Form(None),
        format: str | None = Form(None),
    ) -> TranscribeResponse:
        try:
            body = await audio_file.read()
            input_dto = TranscribeAudioInputDTO(
                audio_bytes=body,
                mime_type=audio_file.content_type or "application/octet-stream",
                language=language,
                file_format=format,
            )
            output = _resolve_transcribe_use_case().execute(input_dto)
            return TranscribeResponse(**output.__dict__)
        except ValidationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except DomainValidationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except DomainError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @router.post("/synthesize")
    async def synthesize(request: SynthesizeRequest) -> Response:
        try:
            input_dto = SynthesizeSpeechInputDTO(
                text=request.text,
                voice=request.voice,
                audio_format=request.format,
                language=request.language,
            )
            output = _resolve_synthesize_use_case().execute(input_dto)
            return Response(content=output.audio_bytes, media_type=output.mime_type)
        except ValidationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except DomainValidationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except DomainError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    return router
