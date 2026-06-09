from pydantic import BaseModel, Field


class SynthesizeRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000)
    voice: str | None = Field(None, max_length=100)
    format: str = Field("mp3", pattern=r"^(mp3|wav|ogg|flac)$")
    language: str | None = Field(None, max_length=10)


class TranscribeResponse(BaseModel):
    text: str
    language: str
    duration_seconds: float | None = None
    confidence: float | None = None
    provider: str
