from functools import lru_cache

try:
    from pydantic_settings import BaseSettings
    from pydantic import Field
except ImportError:  # pragma: no cover
    from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    # Runtime settings loaded from environment variables.
    faster_whisper_model: str = Field("small", env="FASTER_WHISPER_MODEL")
    faster_whisper_device: str = Field("cpu", env="FASTER_WHISPER_DEVICE")
    faster_whisper_compute_type: str = Field("int8", env="FASTER_WHISPER_COMPUTE_TYPE")
    max_stt_concurrency: int = Field(1, env="MAX_STT_CONCURRENCY")
    kokoro_endpoint: str = Field(..., env="KOKORO_ENDPOINT")
    kokoro_api_key: str | None = Field(None, env="KOKORO_API_KEY")
    kokoro_default_voice: str = Field("af_heart", env="KOKORO_DEFAULT_VOICE")
    kokoro_model: str = Field("kokoro", env="KOKORO_MODEL")
    default_audio_format: str = Field("wav", env="DEFAULT_AUDIO_FORMAT")
    kokoro_timeout_seconds: int = Field(30, env="KOKORO_TIMEOUT_SECONDS")
    kokoro_max_retries: int = Field(2, env="KOKORO_MAX_RETRIES")
    kokoro_retry_backoff_seconds: float = Field(0.25, env="KOKORO_RETRY_BACKOFF_SECONDS")
    max_audio_payload_bytes: int = Field(10_485_760, env="MAX_AUDIO_PAYLOAD_BYTES")
    max_tts_text_chars: int = Field(1000, env="MAX_TTS_TEXT_CHARS")
    default_language: str = Field("es", env="DEFAULT_LANGUAGE")

    # Sprint 2/3: LLM & Memory
    google_api_key: str | None = Field(None, env="GOOGLE_API_KEY")
    # gemini-3.1-flash is a verified, deployable model id. A missing LLM_MODEL
    # override must still boot against a real model (see startup probe).
    llm_model: str = Field("models/gemini-3.1-flash-lite", env="LLM_MODEL")
    # IANA timezone used to tell the model the current date/time (see
    # domain/datetime_context). Default: Colombia.
    assistant_timezone: str = Field("America/Bogota", env="ASSISTANT_TIMEZONE")
    # When True, conversational answers are grounded with Google Search so the
    # model can use live web information. Requires a Gemini model that supports
    # the native google_search tool (Gemini 2.x or newer, e.g. 3.1).
    web_search_enabled: bool = Field(True, env="WEB_SEARCH_ENABLED")
    # Cap model output length: bounds worst-case generation time and keeps a phone
    # assistant's answers concise (also curbs rambling/hallucination).
    llm_max_output_tokens: int = Field(768, env="LLM_MAX_OUTPUT_TOKENS")
    llm_intent_max_output_tokens: int = Field(256, env="LLM_INTENT_MAX_OUTPUT_TOKENS")
    qdrant_url: str = Field("http://localhost:6333", env="QDRANT_URL")
    qdrant_api_key: str | None = Field(None, env="QDRANT_API_KEY")
    qdrant_collection: str = Field("memory", env="QDRANT_COLLECTION")
    # Embedding dimensionality. 0 = auto-detect from the embedding model on first
    # use (the robust default: a wrong fixed value here was the cause of the
    # "embeddings failing" mismatch). Set a positive value only to pin a size.
    qdrant_vector_size: int = Field(0, env="QDRANT_VECTOR_SIZE")
    embedding_model: str = Field("models/gemini-embedding-2", env="EMBEDDING_MODEL")

    # Cap on in-memory chat history per session. 20 (~10 turns) is plenty for a
    # phone assistant and keeps the prompt/latency/cost small.
    history_max_messages_per_session: int = Field(20, env="HISTORY_MAX_MESSAGES_PER_SESSION")

    # ReAct orchestrator: max actions per task before forced completion, plus
    # bounds for the per-session action trace store.
    intent_max_steps: int = Field(20, env="INTENT_MAX_STEPS")
    intent_max_sessions: int = Field(1000, env="INTENT_MAX_SESSIONS")
    intent_session_ttl_seconds: int = Field(3600, env="INTENT_SESSION_TTL_SECONDS")

    # Feature flags for graceful degradation. Both default to True so the
    # service is production-capable; at runtime, voice further requires the
    # optional STT/TTS stack to be importable, and memory degrades silently
    # to LLM-only when Qdrant / embeddings are unavailable.
    voice_enabled: bool = Field(True, env="VOICE_ENABLED")
    # Conversational long-term semantic memory (Qdrant) is OFF: short-term
    # history (history_max_messages_per_session) is enough for a phone assistant,
    # and the vector store is now used for the action cache (see skills_* below).
    memory_enabled: bool = Field(False, env="MEMORY_ENABLED")

    # Action cache ("skill memory"): caches resolved single-shot, screen-independent
    # commands (open_app/set_alarm/set_timer/toggle_setting) so a repeated command
    # is answered from Qdrant without calling the LLM. Multi-step/screen-dependent
    # and sensitive actions are never cached (they always go to the LLM).
    #   - hit_threshold: cosine similarity required to reuse a cached action; high
    #     so "abre spotify" never returns the cached "abre whatsapp".
    #   - ttl_days: 0 disables expiry (skills are stable, unlike chat memory).
    skills_enabled: bool = Field(True, env="SKILLS_ENABLED")
    skills_collection: str = Field("skills", env="SKILLS_COLLECTION")
    skills_hit_threshold: float = Field(0.97, env="SKILLS_HIT_THRESHOLD")
    skills_ttl_days: int = Field(0, env="SKILLS_TTL_DAYS")

    # Deploy-only: host port docker-compose maps to the API container (see
    # docker-compose.yml `${VOICE_API_PORT:-8000}:8000`). It lives in `.env`,
    # so Settings must accept it or startup fails with `extra_forbidden`.
    voice_api_port: int = Field(8000, env="VOICE_API_PORT")

    # Memory hygiene — keep the vector store small, clean and relevant.
    #   - min_words: importance filter; turns shorter than this (and without a
    #     fact marker) are NOT persisted (skips greetings/smalltalk).
    #   - dedup_threshold: cosine similarity above which a new memory is treated
    #     as a near-duplicate and skipped (1.0 = identical).
    #   - ttl_days: memories older than this are pruned; 0 disables TTL pruning.
    #   - prune_every: run TTL pruning once per this many stores (throttle).
    memory_min_words: int = Field(4, env="MEMORY_MIN_WORDS")
    memory_dedup_threshold: float = Field(0.95, env="MEMORY_DEDUP_THRESHOLD")
    memory_ttl_days: int = Field(30, env="MEMORY_TTL_DAYS")
    memory_prune_every: int = Field(20, env="MEMORY_PRUNE_EVERY")

    # --- Authentication (HU-27 / ATOM-54) ---
    # MongoDB user store.
    mongo_url: str = Field("mongodb://localhost:27017", env="MONGO_URL")
    mongo_db: str = Field("atom", env="MONGO_DB")
    # Session tokens. Default is RS256 (asymmetric): provide a PEM keypair via
    # JWT_PRIVATE_KEY_PATH / JWT_PUBLIC_KEY_PATH (run scripts/gen_jwt_keys.py for
    # dev). Inline PEMs in JWT_SIGNING_KEY/JWT_VERIFYING_KEY also work. For HS256
    # set JWT_ALGORITHM=HS256 and a shared JWT_SECRET instead.
    jwt_secret: str | None = Field(None, env="JWT_SECRET")
    jwt_algorithm: str = Field("RS256", env="JWT_ALGORITHM")
    jwt_signing_key: str | None = Field(None, env="JWT_SIGNING_KEY")
    jwt_verifying_key: str | None = Field(None, env="JWT_VERIFYING_KEY")
    # RS256 PEM key files (preferred over inline PEMs above).
    jwt_private_key_path: str | None = Field(None, env="JWT_PRIVATE_KEY_PATH")
    jwt_public_key_path: str | None = Field(None, env="JWT_PUBLIC_KEY_PATH")
    jwt_issuer: str = Field("atom-agent", env="JWT_ISSUER")
    jwt_access_ttl_seconds: int = Field(900, env="JWT_ACCESS_TTL_SECONDS")
    jwt_refresh_ttl_seconds: int = Field(2_592_000, env="JWT_REFRESH_TTL_SECONDS")
    # Refresh-token store: Redis when REDIS_URL is set, else in-memory (single instance).
    redis_url: str | None = Field(None, env="REDIS_URL")
    # Google Sign-In: Web client ID used as the ID-token audience. Distinct from
    # GOOGLE_API_KEY (which is for Gemini).
    google_oauth_client_id: str | None = Field(None, env="GOOGLE_OAUTH_CLIENT_ID")
    # Deployment environment. In "production"/"prod" the gRPC server refuses to
    # start without TLS (see infrastructure/grpc/server.py).
    app_env: str = Field("development", env="APP_ENV")
    # gRPC TLS. When both are set the server uses add_secure_port; otherwise it
    # falls back to an INSECURE port (development only).
    tls_cert_path: str | None = Field(None, env="TLS_CERT_PATH")
    tls_key_path: str | None = Field(None, env="TLS_KEY_PATH")

    # --- Hardening (Fase 2A) ---
    # gRPC transport limits (2A.2): cap message size and bound concurrency so a
    # single oversized/abusive client cannot exhaust memory or worker slots.
    grpc_max_message_bytes: int = Field(8 * 1024 * 1024, env="GRPC_MAX_MESSAGE_BYTES")
    grpc_max_concurrent_rpcs: int = Field(64, env="GRPC_MAX_CONCURRENT_RPCS")
    # NOTE: per-RPC handler timeouts (2A.2) are deferred to the gRPC hardening HU
    # (they need each handler wrapped in asyncio.wait_for; no native gRPC option).
    # HTTP hardening (2A.3): per-request body cap + per-client sliding-window rate limit.
    http_max_body_bytes: int = Field(1 * 1024 * 1024, env="HTTP_MAX_BODY_BYTES")
    rate_limit_max_requests: int = Field(120, env="RATE_LIMIT_MAX_REQUESTS")
    rate_limit_window_seconds: float = Field(60.0, env="RATE_LIMIT_WINDOW_SECONDS")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    # Cache settings to avoid re-reading env on each request.
    return Settings()
