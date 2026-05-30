"""
PRISM Analytics — Ingest Service
Orchestrates the full pipeline for a pair of video URLs:
  1. Fetch transcript + metadata for both
  2. Compute engagement rates
  3. Chunk transcripts
  4. Embed + store in Qdrant
  5. Return structured IngestResponse
"""
import uuid
from datetime import datetime, timezone
from app.services.youtube_service import get_youtube_data
from app.services.instagram_service import get_instagram_data
from app.utils.chunker import chunk_transcript
from app.core.vector_store import upsert_chunks
from app.models.schemas import VideoMetadata, IngestResponse


def run_ingest(youtube_url: str, instagram_url: str) -> IngestResponse:
    """
    Full ingest pipeline. Blocking (run via FastAPI's thread pool).
    Returns IngestResponse with metadata for both videos.
    """
    session_id = str(uuid.uuid4())

    # ── Step 1: Fetch raw data ──────────────
    yt_data = get_youtube_data(youtube_url)
    ig_data = get_instagram_data(instagram_url)

    # ── Step 2: Chunk both transcripts ──────
    yt_chunks = chunk_transcript(
        transcript=yt_data["transcript"],
        video_id="A",
        platform="youtube",
    )
    ig_chunks = chunk_transcript(
        transcript=ig_data["transcript"],
        video_id="B",
        platform="instagram",
    )

    # ── Step 3: Embed + store in Qdrant ─────
    upsert_chunks(yt_chunks, session_id=session_id)
    upsert_chunks(ig_chunks, session_id=session_id)

    # ── Step 4: Build response models ───────
    video_a = VideoMetadata(
        video_id="A",
        platform="youtube",
        url=youtube_url,
        title=yt_data["title"],
        creator=yt_data["creator"],
        follower_count=yt_data.get("follower_count"),
        views=yt_data["views"],
        likes=yt_data["likes"],
        comments=yt_data["comments"],
        hashtags=yt_data["hashtags"],
        upload_date=yt_data.get("upload_date"),
        duration_seconds=yt_data.get("duration_seconds"),
        engagement_rate=yt_data["engagement_rate"],
        transcript_chunk_count=len(yt_chunks),
    )

    video_b = VideoMetadata(
        video_id="B",
        platform="instagram",
        url=instagram_url,
        title=ig_data["title"],
        creator=ig_data["creator"],
        follower_count=ig_data.get("follower_count"),
        views=ig_data["views"],
        likes=ig_data["likes"],
        comments=ig_data["comments"],
        hashtags=ig_data["hashtags"],
        upload_date=ig_data.get("upload_date"),
        duration_seconds=ig_data.get("duration_seconds"),
        engagement_rate=ig_data["engagement_rate"],
        transcript_chunk_count=len(ig_chunks),
    )

    return IngestResponse(
        status="success",
        session_id=session_id,
        video_a=video_a,
        video_b=video_b,
        ingested_at=datetime.now(timezone.utc),
    )
