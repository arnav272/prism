"""
PRISM Analytics — YouTube Service

Transcript: youtube-transcript-api (stable, uses YT's own caption endpoint)
Metadata: yt-dlp with graceful fallback — datacenter IPs get bot-detected
by YouTube's anti-bot system. If metadata fails, we use safe defaults and
still get the transcript. Pipeline never crashes.
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
    Uses youtube-transcript-api only — no yt-dlp, no JS runtime needed.
    """
    try:
        from youtube_transcript_api import (
            YouTubeTranscriptApi,
            NoTranscriptFound,
            TranscriptsDisabled,
        )

        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

        # Priority 1: manual English
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

        # Priority 3: any language translated to English
        try:
            t = next(iter(transcript_list))
            entries = t.translate("en").fetch()
            text = " ".join(e["text"] for e in entries).strip()
            if text:
                return text, "translated_captions"
        except Exception:
            pass

    except Exception:
        pass

    return "", "none"


def _get_metadata(url: str, video_id: str) -> dict:
    """
    Attempt yt-dlp metadata fetch.
    Returns empty dict on failure — bot detection on cloud IPs is expected.
    We handle this gracefully instead of crashing.
    """
    try:
        import yt_dlp

        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "simulate": True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
        return info or {}

    except Exception:
        # Bot detection, IP block, or any other yt-dlp failure
        # Return empty dict — caller uses safe defaults
        return {}


def _metadata_from_info(info: dict) -> dict:
    """Extract metrics from yt-dlp info dict."""
    views    = info.get("view_count") or 0
    likes    = info.get("like_count") or 0
    comments = info.get("comment_count") or 0
    hashtags = info.get("tags") or []
    engagement_rate = round(
        (likes + comments) / views * 100, 4
    ) if views > 0 else 0.0

    return {
        "title":           info.get("title", ""),
        "creator":         info.get("uploader") or info.get("channel", ""),
        "follower_count":  info.get("channel_follower_count"),
        "views":           views,
        "likes":           likes,
        "comments":        comments,
        "hashtags":        hashtags[:20],
        "upload_date":     info.get("upload_date"),
        "duration_seconds": info.get("duration"),
        "engagement_rate": engagement_rate,
    }


def get_youtube_data(url: str) -> dict:
    """
    Main entry point. Always returns valid data.

    Production note: Render/cloud datacenter IPs are flagged by YouTube's
    bot detection system, causing yt-dlp metadata extraction to fail.
    youtube-transcript-api is unaffected (uses a different endpoint).
    We return safe defaults for metadata when yt-dlp fails, so the
    transcript pipeline always completes successfully.
    """
    video_id = extract_video_id(url)

    # Get transcript — this always works regardless of IP
    transcript, transcript_source = _get_transcript(video_id)

    # Get metadata — may fail on cloud IPs, handled gracefully
    info = _get_metadata(url, video_id)
    meta = _metadata_from_info(info)

    # If metadata failed, build what we can from the URL and transcript
    if not meta["title"]:
        meta["title"] = f"YouTube Video ({video_id})"
    if not meta["creator"]:
        meta["creator"] = "YouTube Creator"

    # If transcript also failed, use description as fallback
    if not transcript:
        description = info.get("description", "")
        if description:
            transcript = f"Title: {meta['title']}\n\nDescription: {description[:2000]}"
            transcript_source = "metadata_fallback"
        else:
            transcript = f"Title: {meta['title']}. YouTube video ID: {video_id}."
            transcript_source = "id_fallback"

    return {
        "platform":           "youtube",
        "url":                url,
        "title":              meta["title"],
        "creator":            meta["creator"],
        "follower_count":     meta.get("follower_count"),
        "views":              meta["views"],
        "likes":              meta["likes"],
        "comments":           meta["comments"],
        "hashtags":           meta["hashtags"],
        "upload_date":        meta.get("upload_date"),
        "duration_seconds":   meta.get("duration_seconds"),
        "engagement_rate":    meta["engagement_rate"],
        "transcript":         transcript,
        "transcript_source":  transcript_source,
        "video_id_yt":        video_id,
    }