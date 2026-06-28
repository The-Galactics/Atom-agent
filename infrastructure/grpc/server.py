import asyncio
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
from domain.errors import (
    AuthenticationError,
    DomainValidationError,
    InvalidTokenError,
    UserAlreadyExistsError,
)
from domain.user.preferences import confirm_actions_from_settings
from infrastructure.grpc.auth_interceptor import AuthInterceptor, principal_from_context
from infrastructure.grpc.error_interceptor import ErrorInterceptor
from infrastructure.observability.latency import timed

logger = logging.getLogger("voice_module")


def _to_screen(e):
    # Proto ScreenElement -> plain dict the recognizer can render.
    return {
        "text": e.text,
        "role": e.role,
        "clickable": e.clickable,
        "focusable": e.focusable,
        "editable": e.editable,
        "scrollable": e.scrollable,
        "index": e.index,
    }


def _auth_response(pair):
    # domain TokenPair -> proto AuthResponse
    return pb2.AuthResponse(
        access_token=pair.access_token,
        refresh_token=pair.refresh_token,
        expires_in=pair.expires_in,
        user_id=pair.user_id,
    )


class AtomGrpcService(pb2_grpc.AtomAgentServiceServicer):
    def __init__(self, container):
        self.container = container

    # --- Auth (public RPCs; the interceptor lets them through without a token) ---

    async def Register(self, request, context):
        use_case = self.container.register_use_case
        if use_case is None:
            logger.warning("grpc auth unavailable peer=%s status=%s",
                           context.peer(), self.container.auth_status)
            await context.abort(grpc.StatusCode.UNAVAILABLE,
                                "Authentication service is temporarily unavailable")
            return
        try:
            pair = await use_case.execute(request.email, request.password, request.display_name)
        except UserAlreadyExistsError:
            await context.abort(grpc.StatusCode.ALREADY_EXISTS, "email already registered")
            return
        except DomainValidationError:
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT, "invalid email or password")
            return
        return _auth_response(pair)

    async def Login(self, request, context):
        use_case = self.container.authenticate_use_case
        if use_case is None:
            logger.warning("grpc auth unavailable peer=%s status=%s",
                           context.peer(), self.container.auth_status)
            await context.abort(grpc.StatusCode.UNAVAILABLE,
                                "Authentication service is temporarily unavailable")
            return
        try:
            pair = await use_case.execute(request.email, request.password)
        except AuthenticationError:
            # Generic — never reveal whether the email exists (anti-enumeration).
            await context.abort(grpc.StatusCode.UNAUTHENTICATED, "invalid credentials")
            return
        return _auth_response(pair)

    async def AuthenticateWithGoogle(self, request, context):
        use_case = self.container.authenticate_with_google_use_case
        if use_case is None:
            await context.abort(grpc.StatusCode.UNAVAILABLE, "google sign-in unavailable")
            return
        try:
            pair = await use_case.execute(request.id_token)
        except AuthenticationError:
            await context.abort(grpc.StatusCode.UNAUTHENTICATED, "invalid google token")
            return
        return _auth_response(pair)

    async def RefreshToken(self, request, context):
        use_case = self.container.refresh_session_use_case
        if use_case is None:
            logger.warning("grpc auth unavailable peer=%s status=%s",
                           context.peer(), self.container.auth_status)
            await context.abort(grpc.StatusCode.UNAVAILABLE,
                                "Authentication service is temporarily unavailable")
            return
        try:
            pair = await use_case.execute(request.refresh_token)
        except InvalidTokenError:
            await context.abort(grpc.StatusCode.UNAUTHENTICATED, "invalid refresh token")
            return
        return _auth_response(pair)

    async def ExecuteCommand(self, request, context):

        logger.info(
            "grpc_ExecuteCommand peer=%s user_id=%s command=%r",
            context.peer(), request.user_id, request.command,
        )
        use_case = self.container.execute_command_use_case
        if use_case is None:
            detail = getattr(self.container, "intent_status", "intent provider unavailable")
            # Internal status to logs only; the client gets a generic message.
            logger.warning("grpc_ExecuteCommand unavailable peer=%s status=%s", context.peer(), detail)
            await context.abort(
                grpc.StatusCode.UNAVAILABLE,
                "Command service is temporarily unavailable",
            )
            return

        with timed("ExecuteCommand.total"):
            # Identity comes from the token already verified by AuthInterceptor, NOT
            # request.user_id (deprecated) and without re-verifying the signature.
            principal = principal_from_context()
            user_id = principal.user_id if principal else request.user_id

            # Resolve this user's configurable confirmation scope (best-effort): a
            # repo/user miss leaves it None, which falls back to the catalog default.
            confirm_actions = None
            repo = getattr(self.container, "user_repository", None)
            if repo is not None:
                try:
                    with timed("ExecuteCommand.mongo"):
                        user = await repo.find_by_id(user_id)
                    if user is not None:
                        confirm_actions = confirm_actions_from_settings(user.settings)
                except Exception as exc:  # noqa: BLE001 - degrade gracefully
                    logger.warning(
                        "grpc_ExecuteCommand settings_lookup_failed peer=%s error=%s",
                        context.peer(), exc,
                    )

            input_dto = ExecuteCommandInputDTO(
                text=request.command,
                user_id=user_id,
                screen_elements=[_to_screen(e) for e in request.screen_elements],
                order_id=request.order_id or None,
                confirm_actions=confirm_actions,
            )
            # Unhandled errors propagate to the global ErrorInterceptor, which logs the
            # real cause server-side and returns a generic INTERNAL (US-10.1).
            output = await use_case.execute(input_dto)

            logger.info(
                "grpc_ExecuteCommand ok peer=%s action=%s confidence=%.2f step=%d complete=%s",
                context.peer(), output.action_type, output.confidence,
                output.step, output.task_complete,
            )
            return pb2.CommandResponse(
                success=output.success,
                out_message=output.reply_text,
                action_type=output.action_type,
                parameters_json=json.dumps(output.parameters, ensure_ascii=False),
                confidence=output.confidence,
                requires_confirmation=output.requires_confirmation,
                task_complete=output.task_complete,
                step=output.step,
                awaiting_confirmation=output.awaiting_confirmation,
            )

    # --- User settings (protected; identity from the verified token) ---

    async def GetSettings(self, request, context):
        repo = getattr(self.container, "user_repository", None)
        if repo is None:
            await context.abort(grpc.StatusCode.UNAVAILABLE, "Settings service is unavailable")
            return
        principal = principal_from_context()
        if principal is None:
            await context.abort(grpc.StatusCode.UNAUTHENTICATED, "Authentication required")
            return
        user = await repo.find_by_id(principal.user_id)
        settings = user.settings if user is not None else {}
        return pb2.SettingsResponse(settings_json=json.dumps(settings, ensure_ascii=False))

    async def UpdateSettings(self, request, context):
        repo = getattr(self.container, "user_repository", None)
        if repo is None:
            await context.abort(grpc.StatusCode.UNAVAILABLE, "Settings service is unavailable")
            return
        principal = principal_from_context()
        if principal is None:
            await context.abort(grpc.StatusCode.UNAUTHENTICATED, "Authentication required")
            return
        try:
            incoming = json.loads(request.settings_json or "{}")
        except (ValueError, TypeError):
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT, "settings_json must be a JSON object")
            return
        if not isinstance(incoming, dict):
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT, "settings_json must be a JSON object")
            return
        # Sanitize the confirmation scope (drops unknown action types) before
        # persisting, so only valid preferences are stored.
        if isinstance(incoming.get("confirmation"), dict) and "require_for" in incoming["confirmation"]:
            incoming["confirmation"]["require_for"] = sorted(
                confirm_actions_from_settings(incoming)
            )
        current = await repo.find_by_id(principal.user_id)
        merged = {**(current.settings if current is not None else {}), **incoming}
        user = await repo.update_settings(principal.user_id, merged)
        return pb2.SettingsResponse(
            settings_json=json.dumps(user.settings, ensure_ascii=False)
        )

    async def StreamChat(self, request, context):

        logger.info(
            "grpc_StreamChat peer=%s user_id=%s message=%r",
            context.peer(), request.user_id, request.message,
        )
        use_case = self.container.chat_use_case
        if use_case is None:
            # Internal status to logs only; the client gets a generic message.
            logger.warning(
                "grpc_StreamChat unavailable peer=%s status=%s",
                context.peer(), self.container.llm_status,
            )
            await context.abort(
                grpc.StatusCode.UNAVAILABLE,
                "Chat service is temporarily unavailable",
            )
            return

        # Identity comes from the token already verified by AuthInterceptor, NOT
        # request.user_id (deprecated) and without re-verifying the signature.
        principal = principal_from_context()
        session_id = principal.user_id if principal else request.user_id
        input_dto = ChatInputDTO(text=request.message, session_id=session_id)
        # Unhandled errors propagate to the global ErrorInterceptor (US-10.1).
        with timed("StreamChat.total"):
            output = await use_case.execute(input_dto)

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
            logger.warning("grpc_Transcribe unavailable peer=%s status=%s", context.peer(), detail)
            await context.abort(
                grpc.StatusCode.UNAVAILABLE,
                "Voice service is temporarily unavailable",
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
        with timed("Transcribe.total"):
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
            logger.warning("grpc_Synthesize unavailable peer=%s status=%s", context.peer(), detail)
            await context.abort(
                grpc.StatusCode.UNAVAILABLE,
                "Voice service is temporarily unavailable",
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

def grpc_server_options(settings) -> list[tuple[str, int]]:
    """gRPC channel options that cap inbound/outbound message size (Fase 2A.2).

    Bounds memory a single call can force the server to allocate.
    """
    max_bytes = settings.grpc_max_message_bytes
    return [
        ("grpc.max_receive_message_length", max_bytes),
        ("grpc.max_send_message_length", max_bytes),
    ]


def grpc_max_concurrent_rpcs(settings) -> int:
    """Upper bound on RPCs served concurrently (Fase 2A.2 back-pressure)."""
    return settings.grpc_max_concurrent_rpcs


async def serve(container, port: int = 50051):
    settings = container.settings
    # Enforce auth on protected RPCs (public auth RPCs pass through); cap message
    # size and concurrency so one client cannot exhaust memory or worker slots.
    # ErrorInterceptor is outermost so it also sanitizes anything that escapes the
    # auth interceptor or the handlers into a generic INTERNAL (US-10.1).
    server = grpc.aio.server(
        interceptors=[ErrorInterceptor(), AuthInterceptor(container.token_service)],
        options=grpc_server_options(settings),
        maximum_concurrent_rpcs=grpc_max_concurrent_rpcs(settings),
    )
    pb2_grpc.add_AtomAgentServiceServicer_to_server(AtomGrpcService(container), server)

    cert, key = settings.tls_cert_path, settings.tls_key_path
    if cert and key:
        with open(key, "rb") as k, open(cert, "rb") as c:
            credentials = grpc.ssl_server_credentials([(k.read(), c.read())])
        server.add_secure_port(f"[::]:{port}", credentials)
        logger.info("gRPC server (TLS) started on port %d", port)
    elif settings.app_env.lower() in ("production", "prod"):
        # Guardrail: never serve cleartext gRPC in production.
        raise RuntimeError(
            "Refusing to start gRPC without TLS while APP_ENV=production. "
            "Set TLS_CERT_PATH and TLS_KEY_PATH (or run with APP_ENV=development for local dev)."
        )
    else:
        # Development only: no transport encryption. Configure TLS_CERT_PATH /
        # TLS_KEY_PATH for any real deployment.
        server.add_insecure_port(f"[::]:{port}")
        logger.warning("gRPC server started INSECURE (no TLS) on port %d — dev only", port)

    await server.start()
    try:
        await server.wait_for_termination()
    except asyncio.CancelledError:
        # grpc.aio doesn't stop on cancellation — C-core threads keep the process
        # alive. Stop explicitly so the port is freed, then re-raise.
        await server.stop(grace=5)
        raise
