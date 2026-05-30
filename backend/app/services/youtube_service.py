"""
PRISM Analytics — YouTube Service
Extracts transcript + metadata for a YouTube video.
Uses youtube-transcript-api (stable, uses YT's own caption endpoint).
Metadata pulled via yt-dlp (no API key required).
"""
import re
from typing import Optional
from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound, TranscriptsDisabled


def extract_video_id(url: str) -> str:
    """Parse video ID from any YouTube URL format."""
    patterns = [
        r"(?:v=|\/)([0-9A-Za-z_-]{11})",
        r"youtu\.be\/([0-9A-Za-z_-]{11})",
        r"shorts\/([0-9A-Za-z_-]{11})",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    raise ValueError(f"Could not extract video ID from URL: {url}")


def get_transcript(video_id: str) -> str:
    """
    Fetch transcript text. Tries English first, then auto-generated,
    then any available language as last resort.
    """
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

        # Priority 1: manual English
        try:
            transcript = transcript_list.find_transcript(["en"])
        except Exception:
            # Priority 2: auto-generated English
            try:
                transcript = transcript_list.find_generated_transcript(["en"])
            except Exception:
                # Priority 3: first available, translated to English
                transcript = next(iter(transcript_list))
                transcript = transcript.translate("en")

        entries = transcript.fetch()
        return " ".join(entry["text"] for entry in entries).strip()

    except TranscriptsDisabled:
        raise ValueError("Transcripts are disabled for this video.")
    except NoTranscriptFound:
        raise ValueError("No transcript found for this video.")


def get_metadata(url: str) -> dict:
    """
    Pull video metadata using yt-dlp (no API key needed).
    Returns normalized metadata dict.
    """
    try:
        import yt_dlp

        ydl_opts = {
            "quiet": True,
            "skip_download": True,
            "extract_flat": False,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        views     = info.get("view_count") or 0
        likes     = info.get("like_count") or 0
        comments  = info.get("comment_count") or 0
        hashtags  = info.get("tags") or []

        engagement_rate = round((likes + comments) / views * 100, 4) if views > 0 else 0.0

        return {
            "platform":       "youtube",
            "url":            url,
            "title":          info.get("title", "Unknown Title"),
            "creator":        info.get("uploader", "Unknown Creator"),
            "follower_count": info.get("channel_follower_count"),
            "views":          views,
            "likes":          likes,
            "comments":       comments,
            "hashtags":       hashtags[:20],          # cap at 20
            "upload_date":    info.get("upload_date"),
            "duration_seconds": info.get("duration"),
            "engagement_rate": engagement_rate,
        }

    except Exception as e:
        raise ValueError(f"Failed to fetch YouTube metadata: {e}")


def get_youtube_data(url: str) -> dict:
    """
    Main entry point. Returns combined transcript + metadata dict.
    Called by ingest_service.
    """
    video_id = extract_video_id(url)
    transcript = get_transcript(video_id)
    metadata = get_metadata(url)

    return {
        **metadata,
        "video_id_yt": video_id,
        "transcript": transcript,
    }
