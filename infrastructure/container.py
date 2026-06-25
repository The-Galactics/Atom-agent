from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from ports.user_repository_port import UserRepositoryPort

from adapters.speech.faster_whisper_adapter import FasterWhisperAdapter
from adapters.speech.kokoro_adapter import KokoroAdapter
from adapters.llm.gemini_adapter import GeminiAdapter
from adapters.embeddings.gemini_embedding_adapter import GeminiEmbeddingAdapter
from adapters.vector_store.qdrant_adapter import QdrantAdapter
from adapters.history.in_memory_history_adapter import InMemoryHistoryAdapter
from application.agents.nodes import GraphNodes
from application.agents.graph import build_graph
from application.agents.session_store import SessionStore
from application.use_cases.chat import ChatUseCase
from application.use_cases.execute_command import ExecuteCommandUseCase
from application.use_cases.synthesize_speech import SynthesizeSpeechUseCase
from application.use_cases.transcribe_audio import TranscribeAudioUseCase
from application.use_cases.register_user import RegisterUserUseCase
from application.use_cases.authenticate_user import AuthenticateUserUseCase
from application.use_cases.authenticate_with_google import AuthenticateWithGoogleUseCase
from application.use_cases.refresh_session import RefreshSessionUseCase
from ports.token_service_port import TokenServicePort
from domain.value_objects import AudioFormat
from infrastructure.config import Settings
from infrastructure.provider_clients import KokoroClient
from ports.stt_port import SpeechToTextPort
from ports.tts_port import TextToSpeechPort
from ports.llm_port import LLMPort
from ports.vector_store_port import VectorStorePort
from ports.embedding_port import EmbeddingPort
from ports.history_port import HistoryPort
from ports.intent_port import IntentRecognizerPort

logger = logging.getLogger("voice_module")


@dataclass
class AppContainer:
    # Central dependency graph shared by the API layer.
    settings: Settings
    kokoro_client: Optional[KokoroClient]
    stt_adapter: Optional[SpeechToTextPort]
    tts_adapter: Optional[TextToSpeechPort]
    # LLM/memory/chat stack. All None when the Gemini provider can't be built
    # (missing GOOGLE_API_KEY or SDK validation error) so startup degrades to
    # voice/health endpoints instead of crashing.
    llm_adapter: Optional[LLMPort]
    vector_store: Optional[VectorStorePort]
    embedding_adapter: Optional[EmbeddingPort]
    history_adapter: HistoryPort
    transcribe_use_case: Optional[TranscribeAudioUseCase]
    synthesize_use_case: Optional[SynthesizeSpeechUseCase]
    chat_use_case: Optional[ChatUseCase]
    # Order/intent path. None when the function-calling stack is unavailable.
    execute_command_use_case: Optional[ExecuteCommandUseCase] = None
    # Human-readable reason voice is unavailable, when applicable.
    voice_status: str = "ready"
    # Human-readable reason the intent stack is unavailable, when applicable.
    intent_status: str = "ready"
    # Human-readable reason the LLM/chat stack is unavailable, when applicable.
    llm_status: str = "ready"
    # Authentication stack (HU-27). All None when no JWT secret is configured.
    token_service: Optional[TokenServicePort] = None
    register_use_case: Optional[RegisterUserUseCase] = None
    authenticate_use_case: Optional[AuthenticateUserUseCase] = None
    authenticate_with_google_use_case: Optional[AuthenticateWithGoogleUseCase] = None
    refresh_session_use_case: Optional[RefreshSessionUseCase] = None
    user_repository: Optional["UserRepositoryPort"] = None
    auth_status: str = "ready"

    async def ensure_auth_indexes(self) -> None:
        """Create the unique Mongo indexes (email, google_sub). No-op when auth is disabled.

        Best-effort: if MongoDB is unreachable at startup the error is logged as a
        warning and swallowed so the rest of the service (voice/chat) still starts.
        Uniqueness at the use-case layer acts as a safety net until the indexes are
        eventually created on the next successful startup.
        """
        if self.user_repository is not None:
            try:
                await self.user_repository.ensure_indexes()
            except Exception as exc:
                logger.warning("auth_index_init_failed error=%s", exc)

    def shutdown(self) -> None:
        if self.stt_adapter is not None:
            self.stt_adapter.shutdown()

    def readiness(self) -> dict:
        voice_ready = self.transcribe_use_case is not None and self.synthesize_use_case is not None
        return {
            "status": "ok",
            "providers": {
                "stt": {
                    "status": "ready" if self.stt_adapter is not None else "unavailable",
                    "provider": "faster_whisper",
                    "model": self.settings.faster_whisper_model,
                    "detail": None if self.stt_adapter is not None else self.voice_status,
                },
                "tts": {
                    "status": "ready" if self.tts_adapter is not None else "unavailable",
                    "provider": "kokoro",
                    "endpoint": self.settings.kokoro_endpoint,
                    "detail": None if self.tts_adapter is not None else self.voice_status,
                },
                "voice": {
                    "status": "ready" if voice_ready else "degraded",
                    "detail": None if voice_ready else self.voice_status,
                },
                "llm": {
                    "status": (
                        "ready" if self.llm_adapter is not None
                        else "missing_key" if not self.settings.google_api_key
                        else "unavailable"
                    ),
                    "provider": "google/gemini",
                    "model": self.settings.llm_model,
                    "detail": None if self.llm_adapter is not None else self.llm_status,
                },
                "intent": {
                    "status": "ready" if self.execute_command_use_case is not None else "unavailable",
                    "provider": "google/gemini-function-calling",
                    "detail": None if self.execute_command_use_case is not None else self.intent_status,
                },
                "vector_store": {
                    # Lazy + degrade-on-failure: reported "configured" since
                    # connectivity is only proven on first chat turn.
                    "status": "configured" if self.settings.memory_enabled else "disabled",
                    "provider": "qdrant",
                    "url": self.settings.qdrant_url,
                },
                "skills": {
                    # Action cache for repeated single-shot commands (separate
                    # Qdrant collection). Lazy, so reported by config flag.
                    "status": "enabled" if self.settings.skills_enabled else "disabled",
                    "provider": "qdrant",
                    "collection": self.settings.skills_collection,
                },
            },
        }


def _build_voice_adapters(settings: Settings):
    """Construct STT/TTS adapters defensively.

    Returns (kokoro_client, stt_adapter, tts_adapter, status). Any of the
    adapters may be ``None`` when the optional voice stack is unavailable
    (e.g. ``faster_whisper`` not installed) or disabled via config. ``status``
    is a human-readable reason used by readiness() and the voice error paths.
    """
    if not settings.voice_enabled:
        return None, None, None, "voice disabled via VOICE_ENABLED=false"

    kokoro_client = None
    stt_adapter = None
    tts_adapter = None
    status = "ready"

    try:
        kokoro_client = KokoroClient(
            endpoint=settings.kokoro_endpoint,
            api_key=settings.kokoro_api_key,
            timeout_seconds=settings.kokoro_timeout_seconds,
            max_retries=settings.kokoro_max_retries,
            retry_backoff_seconds=settings.kokoro_retry_backoff_seconds,
            model=settings.kokoro_model,
        )
        tts_adapter = KokoroAdapter(
            kokoro_client=kokoro_client,
            default_voice=settings.kokoro_default_voice,
            default_format=AudioFormat.from_string(settings.default_audio_format),
        )
    except Exception as exc:  # pragma: no cover - defensive
        status = f"tts provider unavailable: {exc}"
        logger.warning("tts_init_failed error=%s", exc)
        kokoro_client = None
        tts_adapter = None

    try:
        stt_adapter = FasterWhisperAdapter(
            model_name=settings.faster_whisper_model,
            device=settings.faster_whisper_device,
            compute_type=settings.faster_whisper_compute_type,
            max_concurrency=settings.max_stt_concurrency,
        )
    except Exception as exc:
        # Most commonly: faster_whisper optional dependency not installed.
        status = f"stt provider unavailable: {exc}"
        logger.warning("stt_init_failed error=%s", exc)
        stt_adapter = None

    return kokoro_client, stt_adapter, tts_adapter, status


def _build_intent_use_case(settings: Settings, embedding_adapter: Optional[EmbeddingPort]):
    """Construct the order/intent use case defensively.

    Returns (use_case, status). ``use_case`` is ``None`` when the function-
    calling provider can't be built (missing ``langchain-google-genai``,
    absent API key, etc.), so the order endpoint degrades gracefully.
    Conversational (non-action) utterances resolve to a ``NONE`` action here;
    the client re-routes those to the StreamChat RPC for the grounded reply.

    When ``skills_enabled`` and an embedding adapter is available, the recognizer
    is wrapped in :class:`CachingIntentRecognizer` so repeated single-shot
    commands are served from a Qdrant cache without calling the LLM.
    """
    if not settings.google_api_key:
        return None, "intent provider unavailable: GOOGLE_API_KEY not set"
    try:
        from adapters.intent.gemini_function_calling_adapter import (
            GeminiFunctionCallingAdapter,
        )

        recognizer: IntentRecognizerPort = GeminiFunctionCallingAdapter(
            api_key=settings.google_api_key,
            model=settings.llm_model,
            timezone=settings.assistant_timezone,
        )

        # Action cache: a separate Qdrant collection keyed by command text.
        if settings.skills_enabled and embedding_adapter is not None:
            from adapters.intent.caching_intent_recognizer import (
                CachingIntentRecognizer,
            )

            skills_store = QdrantAdapter(
                url=settings.qdrant_url,
                api_key=settings.qdrant_api_key,
                collection_name=settings.skills_collection,
                embedding_port=embedding_adapter,
                # dedup at the hit threshold so near-identical commands collapse.
                dedup_threshold=settings.skills_hit_threshold,
                ttl_days=settings.skills_ttl_days,
                prune_every=settings.memory_prune_every,
                vector_size=settings.qdrant_vector_size,
            )
            recognizer = CachingIntentRecognizer(
                inner=recognizer,
                vector_store=skills_store,
                hit_threshold=settings.skills_hit_threshold,
            )

        session_store = SessionStore(
            max_steps_per_session=settings.intent_max_steps,
            max_sessions=settings.intent_max_sessions,
            ttl_seconds=settings.intent_session_ttl_seconds,
        )
        use_case = ExecuteCommandUseCase(
            intent_recognizer=recognizer,
            session_store=session_store,
            max_steps=settings.intent_max_steps,
        )
        return use_case, "ready"
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("intent_init_failed error=%s", exc)
        return None, f"intent provider unavailable: {exc}"


def _build_llm_stack(settings: Settings, history_adapter: HistoryPort):
    """Construct the LLM + semantic-memory + chat stack defensively.

    Returns ``(llm_adapter, embedding_adapter, vector_store, chat_use_case,
    status)``. All adapters are ``None`` when the Gemini provider can't be built
    — no ``GOOGLE_API_KEY`` or an SDK validation error — so the service degrades
    to voice/health endpoints instead of crashing at startup. The embedding
    model and Qdrant are lazy (connected on first use), so construction is cheap.
    """
    if not settings.google_api_key:
        return None, None, None, None, "llm provider unavailable: GOOGLE_API_KEY not set"
    try:
        llm_adapter = GeminiAdapter(
            api_key=settings.google_api_key,
            model=settings.llm_model,
            web_search=settings.web_search_enabled,
        )
        embedding_adapter = GeminiEmbeddingAdapter(
            api_key=settings.google_api_key,
            model=settings.embedding_model,
        )
        vector_store = QdrantAdapter(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key,
            collection_name=settings.qdrant_collection,
            embedding_port=embedding_adapter,
            dedup_threshold=settings.memory_dedup_threshold,
            ttl_days=settings.memory_ttl_days,
            prune_every=settings.memory_prune_every,
            vector_size=settings.qdrant_vector_size,
        )
        nodes = GraphNodes(
            llm_adapter, vector_store,
            memory_enabled=settings.memory_enabled,
            memory_min_words=settings.memory_min_words,
            timezone=settings.assistant_timezone,
        )
        graph = build_graph(nodes)
        chat_use_case = ChatUseCase(graph=graph, history_adapter=history_adapter)
        return llm_adapter, embedding_adapter, vector_store, chat_use_case, "ready"
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("llm_init_failed error=%s", exc)
        return None, None, None, None, f"llm provider unavailable: {exc}"


def _load_pem(path: str | None) -> str | None:
    """Read a PEM key file, or return None if no path is set or it is unreadable."""
    if not path:
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except OSError as exc:
        logger.warning("jwt_key_read_failed path=%s error=%s", path, exc)
        return None


def _build_auth_stack(settings: Settings):
    """Construct the authentication stack defensively.

    Returns ``(token_service, register, authenticate, google, refresh, user_repository, status)``.
    All are ``None`` when no JWT secret/signing key is configured (auth disabled),
    so the rest of the service still starts. Mongo/Redis clients connect lazily, so
    this never blocks startup on an unreachable database. Google login is only
    built when ``GOOGLE_OAUTH_CLIENT_ID`` is set (email/password still works).
    """
    alg = (settings.jwt_algorithm or "RS256").upper()
    if alg == "HS256":
        signing_key = settings.jwt_secret or settings.jwt_signing_key
        verifying_key = None  # HS256: the verifying key IS the signing secret.
        if not signing_key:
            return None, None, None, None, None, None, "auth disabled: set JWT_SECRET (HS256)"
    else:
        signing_key = _load_pem(settings.jwt_private_key_path) or settings.jwt_signing_key
        verifying_key = _load_pem(settings.jwt_public_key_path) or settings.jwt_verifying_key
        if not (signing_key and verifying_key):
            return None, None, None, None, None, None, (
                f"auth disabled: {alg} needs a PEM keypair "
                "(set JWT_PRIVATE_KEY_PATH/JWT_PUBLIC_KEY_PATH; run scripts/gen_jwt_keys.py)"
            )
    try:
        from motor.motor_asyncio import AsyncIOMotorClient
        from adapters.user_store.mongo_user_repository import MongoUserRepository
        from adapters.security.argon2_password_hasher import Argon2PasswordHasher
        from adapters.security.jwt_token_service import JwtTokenService
        from adapters.security.in_memory_refresh_token_store import InMemoryRefreshTokenStore

        users = MongoUserRepository(AsyncIOMotorClient(settings.mongo_url), settings.mongo_db)
        hasher = Argon2PasswordHasher()

        if settings.redis_url:
            from redis.asyncio import from_url
            from adapters.security.redis_refresh_token_store import RedisRefreshTokenStore
            refresh_store = RedisRefreshTokenStore(from_url(settings.redis_url))
        else:
            refresh_store = InMemoryRefreshTokenStore()

        tokens = JwtTokenService(
            refresh_store,
            signing_key=signing_key,
            verifying_key=verifying_key,
            algorithm=alg,
            access_ttl_seconds=settings.jwt_access_ttl_seconds,
            refresh_ttl_seconds=settings.jwt_refresh_ttl_seconds,
            issuer=settings.jwt_issuer,
        )

        register = RegisterUserUseCase(users, hasher, tokens)
        authenticate = AuthenticateUserUseCase(users, hasher, tokens)
        refresh = RefreshSessionUseCase(tokens)

        google = None
        if settings.google_oauth_client_id:
            from adapters.security.google_id_token_verifier import GoogleIdTokenVerifier
            verifier = GoogleIdTokenVerifier(settings.google_oauth_client_id)
            google = AuthenticateWithGoogleUseCase(users, verifier, tokens)

        return tokens, register, authenticate, google, refresh, users, "ready"
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("auth_init_failed error=%s", exc)
        return None, None, None, None, None, None, f"auth unavailable: {exc}"


def build_container(settings: Settings) -> AppContainer:
    kokoro_client, stt_adapter, tts_adapter, voice_status = _build_voice_adapters(settings)

    history_adapter = InMemoryHistoryAdapter(
        max_messages_per_session=settings.history_max_messages_per_session,
    )

    # Built defensively: degrades to None (not a crash) when GOOGLE_API_KEY is
    # absent or the Gemini SDK rejects the configuration.
    (
        llm_adapter,
        embedding_adapter,
        vector_store,
        chat_use_case,
        llm_status,
    ) = _build_llm_stack(settings, history_adapter)

    # Voice use cases only exist when their adapters were constructed.
    transcribe_use_case = (
        TranscribeAudioUseCase(
            stt_port=stt_adapter,
            max_audio_payload_bytes=settings.max_audio_payload_bytes,
        )
        if stt_adapter is not None
        else None
    )
    synthesize_use_case = (
        SynthesizeSpeechUseCase(
            tts_port=tts_adapter,
            max_text_chars=settings.max_tts_text_chars,
            default_language=settings.default_language,
        )
        if tts_adapter is not None
        else None
    )

    # Built defensively: degrades to UNAVAILABLE if the provider is misconfigured.
    # Non-action utterances resolve to a NONE action; the client re-routes those
    # to StreamChat (which uses chat_use_case) for the grounded reply.
    execute_command_use_case, intent_status = _build_intent_use_case(settings, embedding_adapter)

    (
        token_service,
        register_use_case,
        authenticate_use_case,
        authenticate_with_google_use_case,
        refresh_session_use_case,
        user_repository,
        auth_status,
    ) = _build_auth_stack(settings)

    if transcribe_use_case is None or synthesize_use_case is None:
        logger.warning("voice_degraded detail=%s", voice_status)
    if chat_use_case is None:
        logger.warning("llm_degraded detail=%s", llm_status)
    if execute_command_use_case is None:
        logger.warning("intent_degraded detail=%s", intent_status)

    return AppContainer(
        settings=settings,
        kokoro_client=kokoro_client,
        stt_adapter=stt_adapter,
        tts_adapter=tts_adapter,
        llm_adapter=llm_adapter,
        vector_store=vector_store,
        embedding_adapter=embedding_adapter,
        history_adapter=history_adapter,
        transcribe_use_case=transcribe_use_case,
        synthesize_use_case=synthesize_use_case,
        chat_use_case=chat_use_case,
        execute_command_use_case=execute_command_use_case,
        voice_status=voice_status,
        intent_status=intent_status,
        llm_status=llm_status,
        token_service=token_service,
        register_use_case=register_use_case,
        authenticate_use_case=authenticate_use_case,
        authenticate_with_google_use_case=authenticate_with_google_use_case,
        refresh_session_use_case=refresh_session_use_case,
        user_repository=user_repository,
        auth_status=auth_status,
    )
