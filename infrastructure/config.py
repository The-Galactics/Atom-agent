from functools import lru_cache

try:
    from pydantic_settings import BaseSettings
    from pydantic import Field
except ImportError:  # pragma: no cover
    from pydantic import BaseSettings, Field


class Settings(BaseSettings):
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

    # Server bind settings (HTTP via uvicorn, gRPC background server).
    http_host: str = Field("0.0.0.0", env="HTTP_HOST")
    http_port: int = Field(8000, env="HTTP_PORT")
    grpc_port: int = Field(50051, env="GRPC_PORT")

    # Sprint 2: LLM & Memory
    nvidia_api_key: str | None = Field(None, env="NVIDIA_API_KEY")
    llm_model: str = Field("google/gemma-3n-e4b-it", env="LLM_MODEL")
    qdrant_url: str = Field("http://localhost:6333", env="QDRANT_URL")
    qdrant_api_key: str | None = Field(None, env="QDRANT_API_KEY")
    qdrant_collection: str = Field("memory", env="QDRANT_COLLECTION")
    embedding_model: str = Field("BAAI/bge-m3", env="EMBEDDING_MODEL")

    # Feature flags for graceful degradation. Both default to True so the
    # service is production-capable; at runtime, voice further requires the
    # optional STT/TTS stack to be importable, and memory degrades silently
    # to LLM-only when Qdrant / embeddings are unavailable.
    voice_enabled: bool = Field(True, env="VOICE_ENABLED")
    memory_enabled: bool = Field(True, env="MEMORY_ENABLED")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
