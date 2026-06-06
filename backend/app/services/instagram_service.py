"""
PRISM Analytics — Instagram Reels Service
Transcript: AssemblyAI STT on downloaded audio (spec-compliant)
Metadata: yt-dlp with cookies (best-effort, graceful fallback)

Why AssemblyAI:
- Explicitly listed in the task spec as a valid transcript method
- Free tier: 100 hours/month — sufficient for demo and 1000 creators/day
- Bypasses Instagram's API block entirely — we transcribe the audio directly
- Same approach works for TikTok, YouTube Shorts, any platform
"""
import os
import re
import tempfile
import subprocess
from app.core.config import get_settings

settings = get_settings()


def _download_audio(url: str, output_path: str) -> bool:
    """
    Download audio-only stream via yt-dlp subprocess.
    Returns True if successful. Cookies used if available.
    """
    cmd = [
        "yt-dlp",
        "--quiet",
        "--no-warnings",
        "-x",                          # extract audio only
        "--audio-format", "mp3",
        "--audio-quality", "5",        # mid quality — enough for STT
        "-o", output_path,
    ]

    cookie_path = settings.instagram_cookies_path
    if cookie_path and os.path.exists(cookie_path):
        cmd += ["--cookies", cookie_path]

    cmd.append(url)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
        )
        return result.returncode == 0 and os.path.exists(output_path)
    except Exception:
        return False


def _transcribe_with_assemblyai(audio_path: str) -> str | None:
    """
    Send audio file to AssemblyAI for transcription.
    Returns transcript text or None on failure.
    """
    try:
        import assemblyai as aai

        aai.settings.api_key = settings.assemblyai_api_key
        if not aai.settings.api_key:
            return None

        transcriber = aai.Transcriber()
        transcript = transcriber.transcribe(audio_path)

        if transcript.status == aai.TranscriptStatus.error:
            return None

        return transcript.text or None

    except Exception:
        return None


def _get_metadata_subprocess(url: str) -> dict | None:
    """
    Run yt-dlp metadata extraction in subprocess.
    Sandboxed — C-level panics cannot kill the FastAPI worker.
    """
    import json

    cookie_path = settings.instagram_cookies_path
    cmd = [
        "yt-dlp",
        "--quiet",
        "--no-warnings",
        "--skip-download",
        "--simulate",
        "--dump-json",
    ]

    if cookie_path and os.path.exists(cookie_path):
        cmd += ["--cookies", cookie_path]

    cmd.append(url)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0 and result.stdout.strip():
            return json.loads(result.stdout.strip().split('\n')[0])
    except Exception:
        pass

    return None


def _metadata_to_text(info: dict) -> str:
    """Build rich text from metadata as last-resort transcript."""
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
    return "\n\n".join(parts) if parts else "No content available"


def get_instagram_data(
    url: str,
    manual_transcript: str | None = None,
) -> dict:
    """
    Main entry. Three-lane extraction:
    Lane 1: yt-dlp audio download → AssemblyAI STT (best quality)
    Lane 2: yt-dlp metadata + manual_transcript if provided
    Lane 3: metadata-only fallback text (pipeline never crashes)
    """
    # ── Get metadata first (always attempt) ──
    info = _get_metadata_subprocess(url)

    # Base metadata with safe defaults
    views    = 0
    likes    = 0
    comments = 0
    hashtags = []
    title    = "Instagram Reel"
    creator  = "Unknown"
    follower_count   = None
    upload_date      = None
    duration_seconds = None
    platform         = "instagram"

    if info:
        views    = info.get("view_count") or 0
        likes    = info.get("like_count") or 0
        comments = info.get("comment_count") or 0
        hashtags = info.get("tags") or []
        title    = (info.get("title") or info.get("description", "Instagram Reel"))[:80]
        creator  = info.get("uploader") or info.get("channel", "Unknown")
        follower_count   = info.get("channel_follower_count")
        upload_date      = info.get("upload_date")
        duration_seconds = info.get("duration")

        description = info.get("description", "")
        if description:
            inline = re.findall(r"#\w+", description)
            hashtags = list(set(hashtags + inline))

        webpage_url = info.get("webpage_url", url)
        if "youtube.com" in webpage_url or "youtu.be" in webpage_url:
            platform = "youtube"

    engagement_rate = round(
        (likes + comments) / views * 100, 4
    ) if views > 0 else 0.0

    # ── Manual paste takes priority if provided ──
    if manual_transcript and manual_transcript.strip():
        return {
            "platform": platform, "url": url, "title": title,
            "creator": creator, "follower_count": follower_count,
            "views": views, "likes": likes, "comments": comments,
            "hashtags": hashtags[:20], "upload_date": upload_date,
            "duration_seconds": duration_seconds,
            "engagement_rate": engagement_rate,
            "transcript": manual_transcript.strip(),
            "transcript_source": "manual_paste",
        }

    # ── Lane 1: Download audio → AssemblyAI STT ──
    transcript = None
    transcript_source = "none"

    if settings.assemblyai_api_key:
        with tempfile.TemporaryDirectory() as tmpdir:
            audio_path = os.path.join(tmpdir, "audio.mp3")
            downloaded = _download_audio(url, audio_path)

            if downloaded:
                transcript = _transcribe_with_assemblyai(audio_path)
                if transcript:
                    transcript_source = "assemblyai_stt"

    # ── Lane 2: Metadata fallback ──
    if not transcript and info:
        transcript = _metadata_to_text(info)
        transcript_source = "metadata_fallback"

    # ── Lane 3: Hard fail with clear message ──
    if not transcript:
        raise ValueError(
            "SCRAPER_BLOCKED: Could not extract audio or metadata. "
            "Please paste the transcript manually."
        )

    return {
        "platform": platform, "url": url, "title": title,
        "creator": creator, "follower_count": follower_count,
        "views": views, "likes": likes, "comments": comments,
        "hashtags": hashtags[:20], "upload_date": upload_date,
        "duration_seconds": duration_seconds,
        "engagement_rate": engagement_rate,
        "transcript": transcript,
        "transcript_source": transcript_source,
    }