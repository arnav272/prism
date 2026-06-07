"""
PRISM Analytics — Instagram Service

Transcript: AssemblyAI STT on downloaded audio (primary)
            Manual paste (user-provided fallback)
            Metadata text (last resort)
Metadata:   yt-dlp subprocess with optional cookies & proxy

Instagram's API blocks all unauthenticated scrapers.
AssemblyAI bypasses this entirely — we transcribe the audio directly
regardless of whether Instagram's API returns metadata.
"""
import os
import re
import subprocess
import json
import tempfile
from app.core.config import get_settings

settings = get_settings()


# ── METADATA ──────────────────────────────────────────────────────

def _get_metadata_subprocess(url: str) -> dict | None:
    """
    Metadata via yt-dlp subprocess.
    Sandboxed — C-level crashes cannot kill FastAPI worker.
    """
    cmd = [
        "yt-dlp", "--quiet", "--no-warnings",
        "--skip-download", "--simulate", "--dump-json",
    ]

    cookie_path = getattr(settings, "instagram_cookies_path", "")
    if cookie_path and os.path.exists(cookie_path):
        cmd += ["--cookies", cookie_path]
        
    # Inject routing proxy right before appending the core URL
    proxy_url = getattr(settings, "proxy_url", "") or ""
    if proxy_url:
        cmd += ["--proxy", proxy_url]
    
    cmd.append(url)

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0 and result.stdout.strip():
            raw = result.stdout.strip().split('\n')[0]
            return json.loads(raw)
    except Exception as e:
        print(f"[PRISM] IG metadata subprocess failed: {e}")

    return None


# ── AUDIO DOWNLOAD ────────────────────────────────────────────────

def _download_audio(url: str, output_path: str) -> bool:
    """Download audio-only stream via yt-dlp subprocess."""
    cmd = [
    "yt-dlp", "--quiet", "--no-warnings",
    "-x",
    "--audio-format", "mp3",
    "--audio-quality", "5",
    "--format", "bestaudio/best",   # ← add this line
    "-o", output_path,
]

    cookie_path = getattr(settings, "instagram_cookies_path", "")
    if cookie_path and os.path.exists(cookie_path):
        cmd += ["--cookies", cookie_path]

    # Inject routing proxy right before appending the core URL
    proxy_url = getattr(settings, "proxy_url", "") or ""
    if proxy_url:
        cmd += ["--proxy", proxy_url]

    cmd.append(url)

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        return result.returncode == 0 and os.path.exists(output_path)
    except Exception as e:
        print(f"[PRISM] IG audio download failed: {e}")
        return False


# ── TRANSCRIPTION ─────────────────────────────────────────────────

def _transcribe_assemblyai(audio_path: str) -> str | None:
    """Send audio to AssemblyAI STT. Returns transcript text or None."""
    try:
        import assemblyai as aai

        api_key = getattr(settings, "assemblyai_api_key", "")
        if not api_key:
            print("[PRISM] AssemblyAI key not set — skipping STT")
            return None

        aai.settings.api_key = api_key
        transcriber = aai.Transcriber()
        transcript  = transcriber.transcribe(audio_path)

        if transcript.status == aai.TranscriptStatus.error:
            print(f"[PRISM] AssemblyAI error: {transcript.error}")
            return None

        text = transcript.text or ""
        if text:
            print(f"[PRISM] IG transcript — assemblyai_stt | {len(text)} chars")
        return text or None

    except Exception as e:
        print(f"[PRISM] AssemblyAI exception: {e}")
        return None


def _extract_inline_captions(info: dict) -> str | None:
    """Try to extract captions from yt-dlp info dict."""
    for source_key in ["automatic_captions", "subtitles"]:
        source = info.get(source_key) or {}
        for lang in ["en", "en-US", "en-GB"]:
            entries = source.get(lang, [])
            texts = [
                e.get("text", "").strip()
                for e in entries
                if isinstance(e, dict) and "url" not in e and e.get("text")
            ]
            result = " ".join(texts).strip()
            if result:
                return result
    return None


def _metadata_to_text(info: dict) -> str:
    """Build fallback text from metadata fields."""
    parts = []
    if info.get("title"):
        parts.append(f"Title: {info['title']}")
    if info.get("uploader") or info.get("channel"):
        parts.append(f"Creator: {info.get('uploader') or info.get('channel')}")
    if info.get("description"):
        parts.append(f"Description: {info['description'][:2000]}")
    tags = info.get("tags") or []
    if tags:
        parts.append(f"Tags: {' '.join(tags[:20])}")
    return "\n\n".join(parts) if parts else ""


# ── MAIN ENTRY ────────────────────────────────────────────────────

def get_instagram_data(url: str, manual_transcript: str | None = None) -> dict:
    """
    Full Instagram pipeline:
    1. Manual paste (highest priority if provided)
    2. yt-dlp inline captions
    3. AssemblyAI STT from downloaded audio
    4. Metadata text fallback

    Never raises — always returns a usable payload.
    """
    # Manual paste takes absolute priority
    if manual_transcript and manual_transcript.strip():
        return _build_response(url, {}, manual_transcript.strip(), "manual_paste")

    # Try metadata via subprocess
    info = _get_metadata_subprocess(url)

    # Try inline captions first (fast, no API call needed)
    if info:
        captions = _extract_inline_captions(info)
        if captions:
            print(f"[PRISM] IG transcript — inline_captions | {len(captions)} chars")
            return _build_response(url, info, captions, "inline_captions")

    # AssemblyAI STT — download audio and transcribe
    assemblyai_key = getattr(settings, "assemblyai_api_key", "")
    if assemblyai_key:
        with tempfile.TemporaryDirectory() as tmpdir:
            audio_path = os.path.join(tmpdir, "audio.mp3")
            downloaded = _download_audio(url, audio_path)
            if downloaded:
                transcript = _transcribe_assemblyai(audio_path)
                if transcript:
                    return _build_response(url, info or {}, transcript, "assemblyai_stt")

    # Metadata text fallback
    if info:
        fallback_text = _metadata_to_text(info)
        if fallback_text:
            print(f"[PRISM] IG transcript — metadata_fallback | {len(fallback_text)} chars")
            return _build_response(url, info, fallback_text, "metadata_fallback")

    # Hard fail → return metadata fallback instead of raising 422
    print(f"[PRISM WARNING] Instagram pipeline exhausted all options for {url}")
    fallback_text = (
        f"Instagram Reel URL: {url}\n"
        f"Note: Audio transcription unavailable on this deployment. "
        f"Paste transcript manually for better analysis."
    )
    return _build_response(url, {}, fallback_text, "pipeline_exhausted")


def _build_response(
    url: str,
    info: dict,
    transcript: str,
    transcript_source: str,
) -> dict:
    """Build normalized response dict from info + transcript."""
    views    = info.get("view_count") or 0
    likes    = info.get("like_count") or 0
    comments = info.get("comment_count") or 0

    hashtags    = info.get("tags") or []
    description = info.get("description", "")
    if description:
        inline_tags = re.findall(r"#\w+", description)
        hashtags    = list(set(hashtags + inline_tags))

    eng_rate = round((likes + comments) / views * 100, 4) if views > 0 else 0.0

    webpage_url = info.get("webpage_url", url)
    platform    = "youtube" if ("youtube.com" in webpage_url or "youtu.be" in webpage_url) else "instagram"

    title = (
        info.get("title")
        or info.get("description", "")[:80]
        or "Instagram Reel"
    )

    return {
        "platform":          platform,
        "url":               url,
        "title":             title,
        "creator":           info.get("uploader") or info.get("channel", "Unknown Creator"),
        "follower_count":    info.get("channel_follower_count"),
        "views":             views,
        "likes":             likes,
        "comments":          comments,
        "hashtags":          hashtags[:20],
        "upload_date":       info.get("upload_date"),
        "duration_seconds":  info.get("duration"),
        "engagement_rate":   eng_rate,
        "transcript":        transcript,
        "transcript_source": transcript_source,
    }