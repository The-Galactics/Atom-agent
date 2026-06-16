from typing import Callable
from fastapi import APIRouter, File, Form, Header, HTTPException, Response, UploadFile
from pydantic import ValidationError
from application.dtos import TranscribeAudioInputDTO, SynthesizeSpeechInputDTO, ChatInputDTO
from application.use_cases.transcribe_audio import TranscribeAudioUseCase
from application.use_cases.synthesize_speech import SynthesizeSpeechUseCase
from application.use_cases.chat import ChatUseCase
from api.schemas import SynthesizeRequest, TranscribeResponse, ChatRequest, ChatResponse
from domain.errors import DomainError, DomainValidationError, ProviderError


UseCaseProvider = Callable[[], TranscribeAudioUseCase] | TranscribeAudioUseCase
UseCaseProviderTts = Callable[[], SynthesizeSpeechUseCase] | SynthesizeSpeechUseCase
UseCaseProviderChat = Callable[[], ChatUseCase] | ChatUseCase


def _error_detail(code: str, message: str, request_id: str | None) -> dict:
    # Standard error payload returned by all endpoints.
    return {
        "error": {
            "code": code,
            "message": message,
            "request_id": request_id,
        }
    }


def create_chat_router(chat_use_case_provider: UseCaseProviderChat) -> APIRouter:
    # Router for chat interactions.
    router = APIRouter(prefix="/chat", tags=["chat"])

    def _resolve_chat_use_case() -> ChatUseCase:
        # Accept direct instance or lazy provider.
        return chat_use_case_provider() if callable(chat_use_case_provider) else chat_use_case_provider

    @router.post("", response_model=ChatResponse)
    async def chat(
        request: ChatRequest,
        x_request_id: str | None = Header(None, alias="X-Request-Id"),
    ) -> ChatResponse:
        try:
            input_dto = ChatInputDTO(
                text=request.text,
                session_id=request.session_id,
            )
            output = await _resolve_chat_use_case().execute(input_dto)
            return ChatResponse(text=output.text, session_id=output.session_id)
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail=_error_detail("CHAT_ERROR", str(exc), x_request_id),
            ) from exc

    return router


def create_voice_router(
    transcribe_use_case_provider: UseCaseProvider,
    synthesize_use_case_provider: UseCaseProviderTts,
    readiness_provider: Callable[[], dict] | None = None,
) -> APIRouter:
    # Router for STT/TTS endpoints.
    router = APIRouter(prefix="/voice", tags=["voice"])

    def _resolve_transcribe_use_case() -> TranscribeAudioUseCase:
        # Accept direct instance or lazy provider.
        return transcribe_use_case_provider() if callable(transcribe_use_case_provider) else transcribe_use_case_provider

    def _resolve_synthesize_use_case() -> SynthesizeSpeechUseCase:
        # Accept direct instance or lazy provider.
        return synthesize_use_case_provider() if callable(synthesize_use_case_provider) else synthesize_use_case_provider

    def _validation_status(message: str) -> int:
        # Map known validation messages to HTTP status codes.
        normalized = message.lower()
        if "exceeds maximum size" in normalized or "too large" in normalized:
            return 413
        if "unsupported" in normalized and ("mime" in normalized or "format" in normalized):
            return 415
        return 400

    @router.post("/transcribe", response_model=TranscribeResponse)
    async def transcribe(
        file: UploadFile = File(...),
        language: str | None = Form(None),
        format: str | None = Form(None),
        beam_size: int = Form(5),
        x_request_id: str | None = Header(None, alias="X-Request-Id"),
    ) -> TranscribeResponse:
        use_case = _resolve_transcribe_use_case()
        if use_case is None:
            raise HTTPException(
                status_code=503,
                detail=_error_detail(
                    "STT_PROVIDER_UNAVAILABLE",
                    "Voice provider unavailable (STT).",
                    x_request_id,
                ),
            )
        try:
            # Build input DTO from multipart request data.
            body = await file.read()
            input_dto = TranscribeAudioInputDTO(
                audio_bytes=body,
                mime_type=file.content_type or "application/octet-stream",
                language=language,
                file_format=format,
                beam_size=beam_size,
            )
            output = use_case.execute(input_dto)
            return TranscribeResponse(**output.__dict__)
        except ValidationError as exc:
            raise HTTPException(
                status_code=400,
                detail=_error_detail("INVALID_REQUEST", str(exc), x_request_id),
            ) from exc
        except DomainValidationError as exc:
            message = str(exc)
            raise HTTPException(
                status_code=_validation_status(message),
                detail=_error_detail("VALIDATION_ERROR", message, x_request_id),
            ) from exc
        except ProviderError as exc:
            raise HTTPException(
                status_code=503,
                detail=_error_detail("STT_PROVIDER_UNAVAILABLE", str(exc), x_request_id),
            ) from exc
        except DomainError as exc:
            raise HTTPException(
                status_code=500,
                detail=_error_detail("DOMAIN_ERROR", str(exc), x_request_id),
            ) from exc

    @router.post("/synthesize")
    async def synthesize(
        request: SynthesizeRequest,
        x_request_id: str | None = Header(None, alias="X-Request-Id"),
    ) -> Response:
        use_case = _resolve_synthesize_use_case()
        if use_case is None:
            raise HTTPException(
                status_code=503,
                detail=_error_detail(
                    "TTS_PROVIDER_UNAVAILABLE",
                    "Voice provider unavailable (TTS).",
                    x_request_id,
                ),
            )
        try:
            # Build input DTO from JSON payload.
            input_dto = SynthesizeSpeechInputDTO(
                text=request.text,
                voice=request.voice,
                audio_format=request.format,
                language=request.language,
                speed=request.speed,
            )
            output = use_case.execute(input_dto)
            headers = {
                "Content-Disposition": f'inline; filename="speech.{output.format}"',
            }
            if output.duration_seconds is not None:
                headers["X-Audio-Duration-Seconds"] = str(output.duration_seconds)
            return Response(content=output.audio_bytes, media_type=output.mime_type, headers=headers)
        except ValidationError as exc:
            raise HTTPException(
                status_code=400,
                detail=_error_detail("INVALID_REQUEST", str(exc), x_request_id),
            ) from exc
        except DomainValidationError as exc:
            message = str(exc)
            raise HTTPException(
                status_code=_validation_status(message),
                detail=_error_detail("VALIDATION_ERROR", message, x_request_id),
            ) from exc
        except ProviderError as exc:
            raise HTTPException(
                status_code=503,
                detail=_error_detail("TTS_PROVIDER_UNAVAILABLE", str(exc), x_request_id),
            ) from exc
        except DomainError as exc:
            raise HTTPException(
                status_code=500,
                detail=_error_detail("DOMAIN_ERROR", str(exc), x_request_id),
            ) from exc

    @router.get("/health")
    async def voice_health() -> dict:
        if readiness_provider is None:
            return {"status": "ok"}
        return readiness_provider()

    return router
