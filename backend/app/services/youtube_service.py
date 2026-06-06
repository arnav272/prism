"""
PRISM Analytics — YouTube Service
Transcript: youtube-transcript-api (stable, fallback handling for datacenter IP blocks)
Metadata:   YouTube Data API v3 (primary, production-grade, free 10K/day)
            yt-dlp (fallback for local dev without API key)
YouTube Data API v3 bypasses datacenter IP bot-detection completely.
Works on Render, Railway, AWS, GCP — any cloud environment.
"""
import re
import requests as http_requests
from app.core.config import get_settings

settings = get_settings()

def extract_video_id(url: str) -> str:
    patterns = [
        r"(?:v=|\/)([0-9A-Za-z_-]{11})",
        r"shorts\/([0-9A-Za-z_-]{11})",
        r"youtu\.be\/([0-9A-Za-z_-]{11})",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    raise ValueError(f"Could not extract video ID from URL: {url}")

def _get_transcript(video_id: str) -> tuple[str, str]:
    """
    Fetch transcript via youtube-transcript-api.
    """
    try:
        from youtube_transcript_api import (
            YouTubeTranscriptApi,
            NoTranscriptFound,
            TranscriptsDisabled,
        )
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

def _get_metadata_via_api(video_id: str) -> dict | None:
    """
    Fetch metadata using YouTube Data API v3.
    Cost: 1 unit per call. Free quota: 10,000 units/day.
    Works from any IP — no bot detection.
    Returns normalized metadata dict or None on failure.
    """
    api_key = settings.youtube_api_key
    if not api_key:
        return None
    try:
        response = http_requests.get(
            "https://www.googleapis.com/youtube/v3/videos",
            params={
                "part":  "snippet,statistics,contentDetails",
                "id":    video_id,
                "key":   api_key,
            },
            timeout=10,
        )
        if response.status_code != 200:
            return None
        data = response.json()
        items = data.get("items", [])
        if not items:
            return None
        item       = items[0]
        snippet    = item.get("snippet", {})
        stats      = item.get("statistics", {})
        details    = item.get("contentDetails", {})
        views    = int(stats.get("viewCount",    0) or 0)
        likes    = int(stats.get("likeCount",    0) or 0)
        comments = int(stats.get("commentCount", 0) or 0)
        engagement_rate = round(
            (likes + comments) / views * 100, 4
        ) if views > 0 else 0.0
        # Parse ISO 8601 duration (PT4M13S → 253 seconds)
        duration_seconds = _parse_iso_duration(details.get("duration", ""))
        # Tags from snippet
        tags = snippet.get("tags") or []
        # Upload date: "2009-10-25T06:57:33Z" → "20091025"
        published = snippet.get("publishedAt", "")
        upload_date = published[:10].replace("-", "") if published else None
        return {
            "title":            snippet.get("title", f"YouTube Video ({video_id})"),
            "creator":          snippet.get("channelTitle", "Unknown Creator"),
            "description":      snippet.get("description", ""),
            "follower_count":   None,  # Requires extra channels API call — omitted
            "views":            views,
            "likes":            likes,
            "comments":         comments,
            "hashtags":         tags[:20],
            "upload_date":      upload_date,
            "duration_seconds": duration_seconds,
            "engagement_rate":  engagement_rate,
        }
    except Exception:
        return None

def _parse_iso_duration(duration: str) -> float | None:
    """
    Parse YouTube's ISO 8601 duration format to seconds.
    Examples: PT4M13S → 253, PT1H2M30S → 3750, PT45S → 45
    """
    if not duration:
        return None
    pattern = r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?"
    match = re.match(pattern, duration)
    if not match:
        return None
    hours   = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    return float(hours * 3600 + minutes * 60 + seconds)

def _get_metadata_via_ytdlp(url: str) -> dict | None:
    """
    Fallback metadata via yt-dlp.
    Works locally, fails on cloud datacenter IPs (YouTube bot detection).
    Used when YOUTUBE_API_KEY is not set.
    """
    try:
        import yt_dlp
        ydl_opts = {
            "quiet":         True,
            "no_warnings":   True,
            "skip_download": True,
            "simulate":      True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
        if not info:
            return None
        views    = info.get("view_count") or 0
        likes    = info.get("like_count") or 0
        comments = info.get("comment_count") or 0
        engagement_rate = round(
            (likes + comments) / views * 100, 4
        ) if views > 0 else 0.0
        published = info.get("upload_date", "")
        return {
            "title":            info.get("title", ""),
            "creator":          info.get("uploader") or info.get("channel", ""),
            "description":      info.get("description", ""),
            "follower_count":   info.get("channel_follower_count"),
            "views":            views,
            "likes":            likes,
            "comments":         comments,
            "hashtags":         (info.get("tags") or [])[:20],
            "upload_date":      published or None,
            "duration_seconds": float(info.get("duration") or 0) or None,
            "engagement_rate":  engagement_rate,
        }
    except Exception:
        return None

def get_youtube_data(url: str) -> dict:
    """
    Main entry point. Priority:
      1. YouTube Data API v3 (cloud-safe, production)
      2. yt-dlp (local dev fallback)
      3. Safe defaults (never crash)
    Transcript fetched independently via youtube-transcript-api.
    """
    video_id = extract_video_id(url)
    # ── Transcript ────────────────────────────────────────────────
    transcript, transcript_source = _get_transcript(video_id)
    # ── Metadata: API v3 → yt-dlp → safe defaults ────────────────
    meta = _get_metadata_via_api(video_id)
    if meta is None:
        meta = _get_metadata_via_ytdlp(url)
    if meta is None:
        meta = {
            "title":            f"YouTube Video ({video_id})",
            "creator":          "YouTube Creator",
            "description":      "",
            "follower_count":   None,
            "views":            0,
            "likes":            0,
            "comments":         0,
            "hashtags":         [],
            "upload_date":      None,
            "duration_seconds": None,
            "engagement_rate":  0.0,
        }
    # ── Transcript fallback ───────────────────────────────────────
    if not transcript or len(transcript.strip()) < 5:
        # Use the description parsed securely by Data API v3 instead of executing blocked yt-dlp subprocesses
        description = meta.get("description", "")
        if description and len(description.strip()) > 10:
            transcript = (
                f"Title: {meta['title']}\n\n"
                f"Description: {description[:2000]}"
            )
            transcript_source = "metadata_fallback"
        else:
            # Build an explicit instructional identity string so the downstream schema validator never runs empty
            transcript = f"Title: {meta['title']}. Creator: {meta['creator']}. YouTube video ID: {video_id}. Tags: {', '.join(meta['hashtags'])}."
            transcript_source = "id_fallback"
            
    print(
        f"[PRISM] YT metadata — "
        f"views: {meta['views']} | likes: {meta['likes']} | "
        f"via: {'api_v3' if settings.youtube_api_key else 'ytdlp'}"
    )
    return {
        "platform":          "youtube",
        "url":               url,
        "title":             meta["title"],
        "creator":           meta["creator"],
        "follower_count":    meta.get("follower_count"),
        "views":             meta["views"],
        "likes":             meta["likes"],
        "comments":          meta["comments"],
        "hashtags":          meta["hashtags"],
        "upload_date":       meta.get("upload_date"),
        "duration_seconds":  meta.get("duration_seconds"),
        "engagement_rate":   meta["engagement_rate"],
        "transcript":        transcript,
        "transcript_source": transcript_source,
        "video_id_yt":       video_id,
    }