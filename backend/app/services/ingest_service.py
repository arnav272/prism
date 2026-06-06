"""
PRISM Analytics — Ingest Service
Builds metadata summary string at ingest time so it can be
injected into every RAG prompt without re-fetching.
"""
import uuid
import traceback
from datetime import datetime, timezone
from pydantic import ValidationError

from app.services.youtube_service import get_youtube_data
from app.services.instagram_service import get_instagram_data
from app.utils.chunker import chunk_transcript
from app.core.vector_store import upsert_chunks
from app.models.schemas import VideoMetadata, IngestResponse

# In-memory session store: session_id → metadata_summary string
SESSION_METADATA: dict[str, str] = {}


def _build_metadata_summary(video_a: VideoMetadata, video_b: VideoMetadata) -> str:
    """
    Builds the metrics block injected into every LLM prompt.
    """
    def fmt(n: int) -> str:
        if n >= 1_000_000_000: return f"{n/1_000_000_000:.2f}B"
        if n >= 1_000_000:     return f"{n/1_000_000:.2f}M"
        if n >= 1_000:         return f"{n/1_000:.1f}K"
        return str(n)

    def eng(v: VideoMetadata) -> str:
        if v.views and v.views > 0:
            return f"{v.engagement_rate:.4f}%"
        return "Incalculable (platform withheld view count)"

    lines = [
        "VIDEO A (YouTube)",
        f"  Title:            {video_a.title}",
        f"  Creator:         {video_a.creator}",
        f"  Followers:       {fmt(video_a.follower_count) if video_a.follower_count else 'N/A'}",
        f"  Views:           {fmt(video_a.views)}",
        f"  Likes:           {fmt(video_a.likes)}",
        f"  Comments:        {fmt(video_a.comments)}",
        f"  Engagement Rate: {eng(video_a)}",
        f"  Upload Date:     {video_a.upload_date or 'N/A'}",
        f"  Duration:        {video_a.duration_seconds}s",
        f"  Hashtags:        {', '.join(video_a.hashtags[:10]) or 'None'}",
        f"  Chunks Indexed:  {video_a.transcript_chunk_count}",
        "",
        "VIDEO B (Instagram)",
        f"  Title:            {video_b.title}",
        f"  Creator:         {video_b.creator}",
        f"  Followers:       {fmt(video_b.follower_count) if video_b.follower_count else 'N/A'}",
        f"  Views:           {fmt(video_b.views) if video_b.views else 'N/A (withheld by platform)'}",
        f"  Likes:           {fmt(video_b.likes)}",
        f"  Comments:        {fmt(video_b.comments)}",
        f"  Engagement Rate: {eng(video_b)}",
        f"  Upload Date:     {video_b.upload_date or 'N/A'}",
        f"  Duration:        {video_b.duration_seconds}s",
        f"  Hashtags:        {', '.join(video_b.hashtags[:10]) or 'None'}",
        f"  Chunks Indexed:  {video_b.transcript_chunk_count}",
    ]
    return "\n".join(lines)


def run_ingest(
    youtube_url: str,
    instagram_url: str,
    manual_transcript_b: str | None = None,
) -> IngestResponse:
    session_id = str(uuid.uuid4())

    # 1. Fetch data from Scrapers
    yt_data = get_youtube_data(youtube_url)
    print(f"[PRISM] YT  — source: {yt_data.get('transcript_source')} | chars: {len(yt_data['transcript'])}")

    ig_data = get_instagram_data(instagram_url, manual_transcript_b)
    print(f"[PRISM] IG  — source: {ig_data.get('transcript_source', 'unknown')} | chars: {len(ig_data.get('transcript', ''))}")

    # 2. Chunking Transcripts
    yt_chunks = chunk_transcript(transcript=yt_data["transcript"], video_id="A", platform="youtube")
    ig_chunks = chunk_transcript(transcript=ig_data.get("transcript", ""), video_id="B", platform="instagram")

    print(f"[PRISM] Chunks — YT: {len(yt_chunks)} | IG: {len(ig_chunks)} | Total: {len(yt_chunks)+len(ig_chunks)}")

    # 3. Save to Vector DB
    upsert_chunks(yt_chunks, session_id=session_id)
    upsert_chunks(ig_chunks, session_id=session_id)

    # 4. Construct Models with explicit error handling for missing platform parameters
    try:
        video_a = VideoMetadata(
            video_id="A", platform="youtube", url=youtube_url,
            title=yt_data.get("title", "Untitled YouTube Video"), creator=yt_data.get("creator", "Unknown Creator"),
            follower_count=yt_data.get("follower_count"),
            views=yt_data.get("views", 0), likes=yt_data.get("likes", 0), comments=yt_data.get("comments", 0),
            hashtags=yt_data.get("hashtags", []), upload_date=yt_data.get("upload_date"),
            duration_seconds=yt_data.get("duration_seconds"),
            engagement_rate=yt_data.get("engagement_rate", 0.0),
            transcript_chunk_count=len(yt_chunks),
        )
    except (ValidationError, KeyError) as err:
        print("\n💥 [PRISM INGEST ERROR] Video A (YouTube) metadata constructor mismatch:")
        print(err)
        raise ValueError(f"YouTube data missing or malformed field: {err}")

    try:
        video_b = VideoMetadata(
            video_id="B", platform=ig_data.get("platform", "instagram"), url=instagram_url,
            title=ig_data.get("title", "Untitled Instagram Video"), creator=ig_data.get("creator", "Unknown Creator"),
            follower_count=ig_data.get("follower_count"),
            views=ig_data.get("views", 0), likes=ig_data.get("likes", 0), comments=ig_data.get("comments", 0),
            hashtags=ig_data.get("hashtags", []), upload_date=ig_data.get("upload_date"),
            duration_seconds=ig_data.get("duration_seconds"),
            engagement_rate=ig_data.get("engagement_rate", 0.0),
            transcript_chunk_count=len(ig_chunks),
        )
    except (ValidationError, KeyError) as err:
        print("\n💥 [PRISM INGEST ERROR] Video B (Instagram) metadata constructor mismatch:")
        if isinstance(err, ValidationError):
            print(err.json(indent=2))
        else:
            print(f"KeyError: {str(err)}")
        print(f"Raw received Instagram payload keys: {list(ig_data.keys())}")
        raise ValueError(f"Instagram data missing or malformed field: {err}")

    # Build and cache metrics summary for this session
    metadata_summary = _build_metadata_summary(video_a, video_b)
    SESSION_METADATA[session_id] = metadata_summary
    print(f"[PRISM] Session {session_id[:8]} ready — metadata cached")

    return IngestResponse(
        status="success",
        session_id=session_id,
        video_a=video_a,
        video_b=video_b,
        ingested_at=datetime.now(timezone.utc),
    )