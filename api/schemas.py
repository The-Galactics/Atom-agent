from pydantic import BaseModel, Field


class SynthesizeRequest(BaseModel):
    # Request schema for text-to-speech generation.
    text: str = Field(..., min_length=1, max_length=1000)
    voice: str | None = Field(None, max_length=100)
    format: str = Field("wav", pattern=r"^(mp3|wav|ogg|flac)$")
    language: str | None = Field(None, max_length=10)
    speed: float = Field(1.0, ge=0.75, le=1.25)


class TranscribeResponse(BaseModel):
    # Response schema returned by speech-to-text endpoint.
    text: str
    language: str
    duration_seconds: float | None = None
    confidence: float | None = None
    provider: str


class ChatRequest(BaseModel):
    # Request schema for chat endpoint.
    text: str = Field(..., min_length=1)
    session_id: str = "default"


class ChatResponse(BaseModel):
    # Response schema for chat endpoint.
    text: str
    session_id: str
