"""
PRISM Analytics — Instagram Reels Service
Extracts transcript (captions) + metadata from an Instagram Reel.

Approach: yt-dlp with session cookies (browser export).
Why: Instagram has no public API for Reels metadata.
     yt-dlp is the only stable free option in dev.

Production note (honest):
  At 1,000 creators/day, Instagram will IP-block without
  proxy rotation. Document this limitation in your Loom.
  Production fix: Bright Data proxy (~$15/mo) or IG Graph API.
"""
import os
import re
import json
import subprocess
from typing import Optional
from app.core.config import get_settings

settings = get_settings()


def _build_ydl_opts() -> dict:
    """Build yt-dlp options. Uses cookie file if configured."""
    opts = {
        "quiet": True,
        "skip_download": True,
        "extract_flat": False,
        "writesubtitles": True,
        "writeautomaticsub": True,
        "subtitleslangs": ["en", "en-US"],
    }

    cookie_path = settings.instagram_cookies_path
    if cookie_path and os.path.exists(cookie_path):
        opts["cookiefile"] = cookie_path

    return opts


def get_instagram_data(url: str) -> dict:
    """
    Main entry point. Pulls metadata + captions for an Instagram Reel.
    Falls back gracefully if captions are unavailable.
    """
    try:
        import yt_dlp

        with yt_dlp.YoutubeDL(_build_ydl_opts()) as ydl:
            info = ydl.extract_info(url, download=False)

        views    = info.get("view_count") or 0
        likes    = info.get("like_count") or 0
        comments = info.get("comment_count") or 0

        # Hashtags: yt-dlp puts them in "tags" or embedded in description
        hashtags = info.get("tags") or []
        description = info.get("description", "")
        if description:
            inline_tags = re.findall(r"#\w+", description)
            hashtags = list(set(hashtags + inline_tags))

        engagement_rate = round((likes + comments) / views * 100, 4) if views > 0 else 0.0

        # Transcript: try auto-captions first
        transcript = _extract_captions(info)

        return {
            "platform":         "instagram",
            "url":              url,
            "title":            info.get("title") or info.get("description", "Instagram Reel")[:80],
            "creator":          info.get("uploader") or info.get("channel", "Unknown Creator"),
            "follower_count":   info.get("channel_follower_count"),
            "views":            views,
            "likes":            likes,
            "comments":         comments,
            "hashtags":         hashtags[:20],
            "upload_date":      info.get("upload_date"),
            "duration_seconds": info.get("duration"),
            "engagement_rate":  engagement_rate,
            "transcript":       transcript,
        }

    except Exception as e:
        raise ValueError(f"Failed to fetch Instagram data: {e}\n"
                         "Tip: Set INSTAGRAM_COOKIES_PATH in .env and export "
                         "cookies from your browser using EditThisCookie extension.")


def _extract_captions(info: dict) -> str:
    """
    Extract caption text from yt-dlp info dict.
    Tries: automatic_captions → subtitles → description fallback.
    """
    # Try automatic captions (most common for Reels)
    auto_captions = info.get("automatic_captions", {})
    for lang in ["en", "en-US", "en-GB"]:
        if lang in auto_captions:
            captions = auto_captions[lang]
            text = _parse_caption_entries(captions)
            if text:
                return text

    # Try manual subtitles
    subtitles = info.get("subtitles", {})
    for lang in ["en", "en-US"]:
        if lang in subtitles:
            text = _parse_caption_entries(subtitles[lang])
            if text:
                return text

    # Last resort: use description as pseudo-transcript
    description = info.get("description", "")
    if description and len(description) > 30:
        return f"[Caption extracted from description]: {description}"

    return "[No transcript available for this Reel]"


def _parse_caption_entries(entries: list) -> str:
    """Parse caption entry list into plain text string."""
    if not entries:
        return ""

    texts = []
    for entry in entries:
        if isinstance(entry, dict):
            # Format: {url, ext} — skip URL-based entries
            if "url" in entry and "ext" in entry:
                continue
            text = entry.get("text", "")
            if text:
                texts.append(text.strip())

    return " ".join(texts).strip()
