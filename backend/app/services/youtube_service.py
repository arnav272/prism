"""
PRISM Analytics — YouTube Service

Transcript priority:
  1. Supadata API (cloud-safe, works on Render, AI fallback built-in)
  2. youtube-transcript-api (local dev fallback)
  3. Metadata description (last resort)

Metadata:
  1. YouTube Data API v3 (cloud-safe, no IP blocks)
  2. yt-dlp (local dev fallback)
  3. Safe defaults (never crash)
"""
import re
import requests as http_requests
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


# ── TRANSCRIPT ────────────────────────────────────────────────────

def _get_transcript(video_id: str) -> tuple[str, str]:
    """
    Priority 1: Supadata API — managed, no IP restrictions, AI fallback.
    Priority 2: youtube-transcript-api — works locally only.
    Returns (text, source_label).
    """
    yt_url = f"https://www.youtube.com/watch?v={video_id}"

    # ── Supadata (production) ─────────────────────────────────────
    supadata_key = getattr(settings, "supadata_api_key", "") or ""
    if supadata_key:
        try:
            from supadata import Supadata, SupadataError

            client     = Supadata(api_key=supadata_key)
            transcript = client.transcript(
                url=yt_url,
                lang="en",
                text=True,
                mode="auto",
            )

            if hasattr(transcript, "content") and transcript.content:
                text = transcript.content
                if isinstance(text, list):
                    text = " ".join(
                        seg.get("text", "") if isinstance(seg, dict) else str(seg)
                        for seg in text
                    ).strip()
                else:
                    text = str(text).strip()

                if text:
                    print(f"[PRISM] YT transcript — supadata_api | {len(text)} chars")
                    return text, "supadata_api"
            else:
                print(f"[PRISM] Supadata YT — empty content returned")

        except Exception as e:
            print(f"[PRISM] Supadata YT exception: {type(e).__name__}: {str(e)[:150]}")

    # ── youtube-transcript-api (local dev fallback) ───────────────
    try:
        from youtube_transcript_api import YouTubeTranscriptApi

        proxy_url = getattr(settings, "proxy_url", "") or ""
        proxies   = {"https": proxy_url, "http": proxy_url} if proxy_url else None

        transcript_list = YouTubeTranscriptApi.list_transcripts(
            video_id, proxies=proxies
        )

        for getter in [
            lambda: transcript_list.find_transcript(["en", "en-US", "en-GB"]),
            lambda: transcript_list.find_generated_transcript(["en", "en-US", "en-GB"]),
            lambda: next(iter(transcript_list)).translate("en"),
        ]:
            try:
                entries = getter().fetch()
                text    = " ".join(e["text"] for e in entries).strip()
                if text:
                    print(f"[PRISM] YT transcript — auto_captions | {len(text)} chars")
                    return text, "auto_captions"
            except Exception:
                continue

    except Exception as e:
        print(f"[PRISM] YT transcript-api blocked: {type(e).__name__}")

    print(f"[PRISM] YT transcript — all methods failed, will use metadata fallback")
    return "", "none"


# ── METADATA ──────────────────────────────────────────────────────

def _get_metadata_via_api_v3(video_id: str) -> dict | None:
    api_key = getattr(settings, "youtube_api_key", "") or ""
    if not api_key:
        return None
    try:
        resp = http_requests.get(
            "https://www.googleapis.com/youtube/v3/videos",
            params={
                "part": "snippet,statistics,contentDetails",
                "id":   video_id,
                "key":  api_key,
            },
            timeout=10,
        )
        if resp.status_code != 200:
            print(f"[PRISM] YouTube API v3 error {resp.status_code}")
            return None

        items = resp.json().get("items", [])
        if not items:
            return None

        item    = items[0]
        snippet = item.get("snippet", {})
        stats   = item.get("statistics", {})
        details = item.get("contentDetails", {})

        views    = int(stats.get("viewCount",    0) or 0)
        likes    = int(stats.get("likeCount",    0) or 0)
        comments = int(stats.get("commentCount", 0) or 0)
        eng_rate = round((likes + comments) / views * 100, 4) if views > 0 else 0.0

        published   = snippet.get("publishedAt", "")
        upload_date = published[:10].replace("-", "") if published else None

        print(f"[PRISM] YT metadata via api_v3 — views: {views} | likes: {likes} | comments: {comments}")

        return {
            "title":            snippet.get("title", ""),
            "creator":          snippet.get("channelTitle", ""),
            "follower_count":   None,
            "views":            views,
            "likes":            likes,
            "comments":         comments,
            "hashtags":         (snippet.get("tags") or [])[:20],
            "upload_date":      upload_date,
            "duration_seconds": _parse_iso_duration(details.get("duration", "")),
            "engagement_rate":  eng_rate,
            "description":      snippet.get("description", ""),
        }
    except Exception as e:
        print(f"[PRISM] YouTube API v3 exception: {e}")
        return None


def _parse_iso_duration(duration: str) -> float | None:
    if not duration:
        return None
    m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", duration)
    if not m:
        return None
    return float(int(m.group(1) or 0) * 3600 + int(m.group(2) or 0) * 60 + int(m.group(3) or 0))


def _get_metadata_via_ytdlp(url: str) -> dict | None:
    try:
        import yt_dlp
        with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True, "skip_download": True}) as ydl:
            info = ydl.extract_info(url, download=False)
        if not info:
            return None
        views    = info.get("view_count") or 0
        likes    = info.get("like_count") or 0
        comments = info.get("comment_count") or 0
        eng_rate = round((likes + comments) / views * 100, 4) if views > 0 else 0.0
        print(f"[PRISM] YT metadata via ytdlp — views: {views}")
        return {
            "title":            info.get("title", ""),
            "creator":          info.get("uploader") or info.get("channel", ""),
            "follower_count":   info.get("channel_follower_count"),
            "views":            views, "likes": likes, "comments": comments,
            "hashtags":         (info.get("tags") or [])[:20],
            "upload_date":      info.get("upload_date"),
            "duration_seconds": float(info.get("duration") or 0) or None,
            "engagement_rate":  eng_rate,
            "description":      info.get("description", ""),
        }
    except Exception as e:
        print(f"[PRISM] yt-dlp metadata failed (expected on cloud): {type(e).__name__}")
        return None


# ── MAIN ENTRY ────────────────────────────────────────────────────

def get_youtube_data(url: str) -> dict:
    video_id = extract_video_id(url)

    # Transcript — independent of metadata
    transcript, transcript_source = _get_transcript(video_id)

    # Metadata — API v3 → yt-dlp → safe defaults
    meta = _get_metadata_via_api_v3(video_id)
    if meta is None:
        meta = _get_metadata_via_ytdlp(url)
    if meta is None:
        meta = {
            "title": f"YouTube Video ({video_id})",
            "creator": "YouTube Creator",
            "follower_count": None,
            "views": 0, "likes": 0, "comments": 0,
            "hashtags": [], "upload_date": None,
            "duration_seconds": None, "engagement_rate": 0.0,
            "description": "",
        }

    # Transcript fallback — use description if all else failed
    if not transcript:
        description = meta.get("description", "")
        if description and len(description) > 50:
            transcript = f"Title: {meta['title']}\n\nDescription: {description[:3000]}"
            transcript_source = "metadata_fallback"
            print(f"[PRISM] YT transcript — using description fallback | {len(transcript)} chars")
        else:
            transcript = f"Title: {meta['title']}. Video ID: {video_id}."
            transcript_source = "id_fallback"

    print(f"[PRISM] YT  — source: {transcript_source} | chars: {len(transcript)}")

    return {
        "platform":          "youtube",
        "url":               url,
        "title":             meta["title"] or f"YouTube Video ({video_id})",
        "creator":           meta["creator"] or "Unknown Creator",
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
