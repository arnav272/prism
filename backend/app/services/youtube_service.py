"""
PRISM Analytics — YouTube Service

Metadata:   YouTube Data API v3 (primary — works on any cloud IP)
            yt-dlp (local fallback — fails on Render/datacenter IPs)
Transcript: youtube-transcript-api (always attempted first)
            Description text (last resort fallback)

These two pipelines are fully independent. Metadata success/failure
does not affect transcript extraction and vice versa.
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
    Priority 1: youtube-transcript-api (blocked on Render IPs)
    Priority 2: AssemblyAI direct URL transcription (no download needed)
    """
    # Try youtube-transcript-api first
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
        print(f"[PRISM] YT transcript — caption API blocked: {type(e).__name__}")

    # AssemblyAI direct URL — no audio download required
    assemblyai_key = getattr(settings, "assemblyai_api_key", "") or ""
    if assemblyai_key:
        print(f"[PRISM] YT transcript — trying AssemblyAI direct URL")
        try:
            import assemblyai as aai
            aai.settings.api_key = assemblyai_key

            yt_url = f"https://www.youtube.com/watch?v={video_id}"
            transcriber = aai.Transcriber()
            transcript  = transcriber.transcribe(yt_url)

            if transcript.status == aai.TranscriptStatus.completed and transcript.text:
                text = transcript.text.strip()
                print(f"[PRISM] YT transcript — assemblyai_direct | {len(text)} chars")
                return text, "assemblyai_direct"
            else:
                print(f"[PRISM] YT AssemblyAI error: {transcript.error}")
        except Exception as e:
            print(f"[PRISM] YT AssemblyAI exception: {e}")

    print(f"[PRISM] YT transcript — falling back to metadata description")
    return "", "none"

# ── METADATA ──────────────────────────────────────────────────────

def _get_metadata_via_api_v3(video_id: str) -> dict | None:
    """
    YouTube Data API v3 — production-grade, no IP restrictions.
    10,000 units/day free. Each video lookup costs 1 unit.
    """
    api_key = getattr(settings, "youtube_api_key", "")
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
            print(f"[PRISM] YouTube API v3 error {resp.status_code}: {resp.text[:200]}")
            return None

        data  = resp.json()
        items = data.get("items", [])
        if not items:
            print(f"[PRISM] YouTube API v3 — no items returned for {video_id}")
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
            "title":            snippet.get("title", f"YouTube Video ({video_id})"),
            "creator":          snippet.get("channelTitle", "Unknown Creator"),
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
    h, mi, s = int(m.group(1) or 0), int(m.group(2) or 0), int(m.group(3) or 0)
    return float(h * 3600 + mi * 60 + s)


def _get_metadata_via_ytdlp(url: str) -> dict | None:
    """Local dev fallback — fails on cloud datacenter IPs."""
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

        print(f"[PRISM] YT metadata via ytdlp — views: {views} | likes: {likes}")
        return {
            "title":            info.get("title", ""),
            "creator":          info.get("uploader") or info.get("channel", ""),
            "follower_count":   info.get("channel_follower_count"),
            "views":            views,
            "likes":            likes,
            "comments":         comments,
            "hashtags":         (info.get("tags") or [])[:20],
            "upload_date":      info.get("upload_date"),
            "duration_seconds": float(info.get("duration") or 0) or None,
            "engagement_rate":  eng_rate,
            "description":      info.get("description", ""),
        }
    except Exception as e:
        print(f"[PRISM] yt-dlp metadata failed (expected on cloud): {e}")
        return None


# ── MAIN ENTRY ────────────────────────────────────────────────────

def get_youtube_data(url: str) -> dict:
    """
    Full pipeline. Transcript and metadata fetched independently.
    Neither blocks the other from succeeding.
    """
    video_id = extract_video_id(url)

    # Step 1: Transcript (always try first, independent of metadata)
    transcript, transcript_source = _get_transcript(video_id)

    # Step 2: Metadata — API v3 → yt-dlp → safe defaults
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

    # Step 3: If no spoken transcript, use description as fallback
    # This is a LAST RESORT — transcript_source logs make it visible
    if not transcript:
        description = meta.get("description", "")
        if description and len(description) > 50:
            transcript = (
                f"Title: {meta['title']}\n\n"
                f"Description: {description[:3000]}"
            )
            transcript_source = "metadata_fallback"
            print(f"[PRISM] YT transcript — using description fallback | {len(transcript)} chars")
        else:
            transcript = f"Title: {meta['title']}. Video ID: {video_id}."
            transcript_source = "id_fallback"
            print(f"[PRISM] YT transcript — id_fallback only. Captions may be disabled on this video.")

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
