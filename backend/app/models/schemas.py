"""
PRISM Analytics — Pydantic Schemas
All request/response models. Protected namespace fix applied.
"""
try:
    from pydantic import BaseModel, ConfigDict
except Exception:
    # Fallback stubs for environments where pydantic isn't installed
    from typing import Any

    class BaseModel:
        def __init__(self, **kwargs: Any) -> None:
            for k, v in kwargs.items():
                setattr(self, k, v)

    class ConfigDict(dict):
        pass

from typing import Optional, Literal
from datetime import datetime


class IngestRequest(BaseModel):
    youtube_url: str
    instagram_url: str
    manual_transcript_b: Optional[str] = None


class VideoMetadata(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    video_id: Literal["A", "B"]
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
    transcript_chunk_count: int


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
    video_id: Literal["A", "B"]
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
