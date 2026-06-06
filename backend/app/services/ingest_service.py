"""
PRISM Analytics — Ingest Service
Builds metadata summary string at ingest time so it can be
injected into every RAG prompt without re-fetching.
"""
import uuid
from datetime import datetime, timezone
from app.services.youtube_service import get_youtube_data
from app.services.instagram_service import get_instagram_data
from app.utils.chunker import chunk_transcript
from app.core.vector_store import upsert_chunks
from app.models.schemas import VideoMetadata, IngestResponse

# In-memory session store: session_id → metadata_summary string
# Cleared on process restart — sufficient for demo scale
SESSION_METADATA: dict[str, str] = {}


def _build_metadata_summary(video_a: VideoMetadata, video_b: VideoMetadata) -> str:
    """
    Builds the metrics block injected into every LLM prompt.
    Explicit and unambiguous so the model never claims it lacks data.
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
        f"  Title:           {video_a.title}",
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
        f"  Title:           {video_b.title}",
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

    yt_data = get_youtube_data(youtube_url)
    print(f"[PRISM] YT  — source: {yt_data.get('transcript_source')} | chars: {len(yt_data['transcript'])}")

    ig_data = get_instagram_data(instagram_url, manual_transcript_b)
    print(f"[PRISM] IG  — source: {ig_data.get('transcript_source')} | chars: {len(ig_data['transcript'])}")

    yt_chunks = chunk_transcript(transcript=yt_data["transcript"], video_id="A", platform="youtube")
    ig_chunks = chunk_transcript(transcript=ig_data["transcript"], video_id="B", platform="instagram")

    print(f"[PRISM] Chunks — YT: {len(yt_chunks)} | IG: {len(ig_chunks)} | Total: {len(yt_chunks)+len(ig_chunks)}")

    upsert_chunks(yt_chunks, session_id=session_id)
    upsert_chunks(ig_chunks, session_id=session_id)

    video_a = VideoMetadata(
        video_id="A", platform="youtube", url=youtube_url,
        title=yt_data["title"], creator=yt_data["creator"],
        follower_count=yt_data.get("follower_count"),
        views=yt_data["views"], likes=yt_data["likes"], comments=yt_data["comments"],
        hashtags=yt_data["hashtags"], upload_date=yt_data.get("upload_date"),
        duration_seconds=yt_data.get("duration_seconds"),
        engagement_rate=yt_data["engagement_rate"],
        transcript_chunk_count=len(yt_chunks),
    )

    video_b = VideoMetadata(
        video_id="B", platform=ig_data.get("platform", "instagram"), url=instagram_url,
        title=ig_data["title"], creator=ig_data["creator"],
        follower_count=ig_data.get("follower_count"),
        views=ig_data["views"], likes=ig_data["likes"], comments=ig_data["comments"],
        hashtags=ig_data["hashtags"], upload_date=ig_data.get("upload_date"),
        duration_seconds=ig_data.get("duration_seconds"),
        engagement_rate=ig_data["engagement_rate"],
        transcript_chunk_count=len(ig_chunks),
    )

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