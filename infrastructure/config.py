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
    # gemini-3.1-flash-lite is cheaper and exposes the native google_search tool.
    llm_model: str = Field("gemini-3.1-flash-lite", env="LLM_MODEL")
    # IANA timezone used to tell the model the current date/time (see
    # domain/datetime_context). Default: Colombia.
    assistant_timezone: str = Field("America/Bogota", env="ASSISTANT_TIMEZONE")
    # When True, conversational answers are grounded with Google Search so the
    # model can use live web information. Requires a Gemini 2.x model.
    web_search_enabled: bool = Field(True, env="WEB_SEARCH_ENABLED")
    qdrant_url: str = Field("http://localhost:6333", env="QDRANT_URL")
    qdrant_api_key: str | None = Field(None, env="QDRANT_API_KEY")
    qdrant_collection: str = Field("memory", env="QDRANT_COLLECTION")
    # Embedding dimensionality — MUST match the output dim of `embedding_model`,
    # or the Qdrant collection and the vectors mismatch and memory silently
    # breaks. gemini-embedding-001 produces 3072-dim vectors (keep both in sync).
    qdrant_vector_size: int = Field(3072, env="QDRANT_VECTOR_SIZE")
    embedding_model: str = Field("models/gemini-embedding-001", env="EMBEDDING_MODEL")

    # Cap on in-memory chat history per session to bound memory growth in
    # long-running deployments (oldest messages are dropped past this limit).
    history_max_messages_per_session: int = Field(50, env="HISTORY_MAX_MESSAGES_PER_SESSION")

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
    memory_enabled: bool = Field(True, env="MEMORY_ENABLED")

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

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    # Cache settings to avoid re-reading env on each request.
    return Settings()
