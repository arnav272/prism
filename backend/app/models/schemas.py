"""
PRISM Analytics — Pydantic Schemas
All request/response models. Protected namespace fix applied.
"""
from typing import Optional, Literal, Any
from datetime import datetime

try:
    from pydantic import BaseModel, ConfigDict
except Exception:
    # Fallback stubs for environments where pydantic isn't installed
    class BaseModel:
        def __init__(self, **kwargs: Any) -> None:
            for k, v in kwargs.items():
                setattr(self, k, v)

    class ConfigDict(dict):
        pass


class IngestRequest(BaseModel):
    youtube_url: str
    instagram_url: str
    manual_transcript_b: Optional[str] = None


class VideoMetadata(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    video_id: Optional[Literal["A", "B"]] = None  # Populated dynamically by ingest logic
    platform: str
    url: str
    title: str
    creator: str
    follower_count: Optional[int] = None
    views: int
    likes: int
    comments: int
    hashtags: list[str] = []
    upload_date: Optional[str] = None
    duration_seconds: Optional[float] = None
    engagement_rate: float
    transcript_chunk_count: int = 0  # Fix: Defaulted to 0 so raw scrapers don't fail validation before chunking


class IngestResponse(BaseModel):
    status: str
    session_id: str
    video_a: VideoMetadata
    video_b: VideoMetadata
    ingested_at: datetime


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    session_id: str
    message: str
    history: list[ChatMessage] = []


class SourceChunk(BaseModel):
    video_id: Literal["A", "B"] = "A"
    platform: str
    chunk_text: str
    chunk_index: int
    score: float


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceChunk]
    model_used: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    qdrant: str
    gemini_key_set: bool
    groq_key_set: bool
    embedding_model: str