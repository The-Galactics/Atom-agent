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

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
