"""
PRISM Analytics — Pydantic Schemas
All request/response models for the API layer.
"""
from pydantic import BaseModel, HttpUrl
from typing import Optional, Literal
from datetime import datetime


# ── Ingest ───────────────────────────────

class IngestRequest(BaseModel):
    youtube_url: str
    instagram_url: str


class VideoMetadata(BaseModel):
    video_id: Literal["A", "B"]
    platform: Literal["youtube", "instagram"]
    url: str
    title: str
    creator: str
    follower_count: Optional[int] = None
    views: int
    likes: int
    comments: int
    hashtags: list[str] = []
    upload_date: Optional[str] = None
    duration_seconds: Optional[int] = None
    engagement_rate: float          # Computed: (likes + comments) / views * 100
    transcript_chunk_count: int


class IngestResponse(BaseModel):
    status: str
    session_id: str
    video_a: VideoMetadata          # YouTube
    video_b: VideoMetadata          # Instagram
    ingested_at: datetime


# ── Chat ─────────────────────────────────

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
    score: float                    # Cosine similarity score


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceChunk]
    model_used: str                 # Which LLM answered: gemini | groq
    tokens_used: Optional[int] = None


# ── Health ───────────────────────────────

class HealthResponse(BaseModel):
    status: str
    qdrant: str
    gemini: str
    groq: str
    embedding_model: str
