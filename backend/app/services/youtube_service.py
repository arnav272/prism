"""
PRISM Analytics — YouTube Service
Transcript: youtube-transcript-api (stable, no JS runtime needed)
Metadata: yt-dlp (metadata-only, no format resolution = no JS challenge)
"""
import re
from app.core.config import get_settings

settings = get_settings()


def extract_video_id(url: str) -> str:
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


def _get_transcript(video_id: str) -> tuple[str, str]:
    """
    Returns (transcript_text, source_label).
    Tries manual EN → auto-generated EN → any language translated.
    Uses youtube-transcript-api only — no yt-dlp, no JS runtime needed.
    """
    from youtube_transcript_api import (
        YouTubeTranscriptApi,
        NoTranscriptFound,
        TranscriptsDisabled,
    )

    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

        # Priority 1: manual English captions
        try:
            t = transcript_list.find_transcript(["en", "en-US", "en-GB"])
            entries = t.fetch()
            text = " ".join(e["text"] for e in entries).strip()
            if text:
                return text, "manual_captions"
        except Exception:
            pass

        # Priority 2: auto-generated English
        try:
            t = transcript_list.find_generated_transcript(["en", "en-US", "en-GB"])
            entries = t.fetch()
            text = " ".join(e["text"] for e in entries).strip()
            if text:
                return text, "auto_captions"
        except Exception:
            pass

        # Priority 3: first available, translated to English
        try:
            t = next(iter(transcript_list))
            entries = t.translate("en").fetch()
            text = " ".join(e["text"] for e in entries).strip()
            if text:
                return text, "translated_captions"
        except Exception:
            pass

    except (TranscriptsDisabled, NoTranscriptFound):
        pass
    except Exception:
        pass

    return "", "none"


def _get_metadata(url: str) -> dict:
    """
    Metadata-only yt-dlp call.
    Key: extract_flat=True skips format resolution entirely,
    which is what triggers the JS challenge. Safe and fast.
    """
    import yt_dlp

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "extract_flat": False,
        # These flags prevent yt-dlp from attempting format downloads
        # which is what triggers the JS/n-challenge errors
        "listformats": False,
        "simulate": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    return info


def _metadata_to_text(info: dict) -> str:
    """Build rich text from metadata when transcript unavailable."""
    parts = []
    if info.get("title"):
        parts.append(f"Title: {info['title']}")
    if info.get("uploader") or info.get("channel"):
        parts.append(f"Creator: {info.get('uploader') or info.get('channel')}")
    if info.get("description"):
        parts.append(f"Description: {info['description'][:2000]}")
    tags = info.get("tags") or []
    if tags:
        parts.append(f"Tags: {', '.join(tags[:30])}")
    chapters = info.get("chapters") or []
    if chapters:
        chapter_titles = " | ".join(
            c.get("title", "") for c in chapters if c.get("title")
        )
        if chapter_titles:
            parts.append(f"Chapters: {chapter_titles}")
    return "\n\n".join(parts)


def get_youtube_data(url: str) -> dict:
    """
    Main entry. Always returns valid data — never crashes pipeline.
    Transcript via youtube-transcript-api.
    Metadata via yt-dlp simulate mode (no JS challenge).
    """
    video_id = extract_video_id(url)

    # Get metadata first
    try:
        info = _get_metadata(url)
    except Exception as e:
        raise ValueError(f"Failed to fetch YouTube metadata: {e}")

    views    = info.get("view_count") or 0
    likes    = info.get("like_count") or 0
    comments = info.get("comment_count") or 0
    hashtags = info.get("tags") or []
    engagement_rate = round(
        (likes + comments) / views * 100, 4
    ) if views > 0 else 0.0

    # Get transcript independently — failure never blocks metadata
    transcript, transcript_source = _get_transcript(video_id)

    if not transcript:
        transcript = _metadata_to_text(info)
        transcript_source = "metadata_fallback"

    return {
        "platform":           "youtube",
        "url":                url,
        "title":              info.get("title", "Unknown Title"),
        "creator":            info.get("uploader") or info.get("channel", "Unknown"),
        "follower_count":     info.get("channel_follower_count"),
        "views":              views,
        "likes":              likes,
        "comments":           comments,
        "hashtags":           hashtags[:20],
        "upload_date":        info.get("upload_date"),
        "duration_seconds":   info.get("duration"),
        "engagement_rate":    engagement_rate,
        "transcript":         transcript,
        "transcript_source":  transcript_source,
        "video_id_yt":        video_id,
    }