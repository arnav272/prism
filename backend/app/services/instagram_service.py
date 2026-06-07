"""
PRISM Analytics — Instagram Service

Transcript priority:
  1. Supadata API (cloud-safe, handles IP blocks, AI fallback built-in)
  2. Inline captions via yt-dlp
  3. AssemblyAI STT on downloaded audio
  4. Metadata text fallback
  5. Graceful placeholder (never crashes)

Manual paste always takes priority if provided.
"""
import os
import re
import subprocess
import json
import tempfile
from app.core.config import get_settings

settings = get_settings()


# ── SUPADATA ──────────────────────────────────────────────────────

def _transcribe_via_supadata(url: str) -> str | None:
    """
    Supadata transcript API — works on any cloud IP.
    Handles Instagram, YouTube, TikTok, Twitter.
    100 free requests/month, no credit card.
    """
    supadata_key = getattr(settings, "supadata_api_key", "") or ""
    if not supadata_key:
        return None

    try:
        from supadata import Supadata, SupadataError

        client     = Supadata(api_key=supadata_key)
        transcript = client.transcript(
            url=url,
            lang="en",
            text=True,
            mode="auto",
        )

        if hasattr(transcript, "content") and transcript.content:
            content = transcript.content
            if isinstance(content, list):
                text = " ".join(
                    seg.get("text", "") if isinstance(seg, dict) else str(seg)
                    for seg in content
                ).strip()
            else:
                text = str(content).strip()

            if text:
                print(f"[PRISM] IG transcript — supadata_api | {len(text)} chars")
                return text

        print(f"[PRISM] Supadata IG — empty content returned")
        return None

    except Exception as e:
        print(f"[PRISM] Supadata IG exception: {type(e).__name__}: {str(e)[:150]}")
        return None


# ── METADATA ──────────────────────────────────────────────────────

def _get_metadata_subprocess(url: str) -> dict | None:
    """yt-dlp metadata in subprocess — sandboxed, C panics can't kill FastAPI."""
    cmd = [
        "yt-dlp", "--quiet", "--no-warnings",
        "--skip-download", "--simulate", "--dump-json",
    ]

    proxy_url = getattr(settings, "proxy_url", "") or ""
    if proxy_url:
        cmd += ["--proxy", proxy_url]

    cookie_path = getattr(settings, "instagram_cookies_path", "") or ""
    if cookie_path and os.path.exists(cookie_path):
        cmd += ["--cookies", cookie_path]

    cmd.append(url)

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0 and result.stdout.strip():
            return json.loads(result.stdout.strip().split('\n')[0])
    except Exception as e:
        print(f"[PRISM] IG metadata subprocess: {type(e).__name__}: {str(e)[:100]}")

    return None


# ── INLINE CAPTIONS ───────────────────────────────────────────────

def _extract_inline_captions(info: dict) -> str | None:
    for source_key in ["automatic_captions", "subtitles"]:
        source = info.get(source_key) or {}
        for lang in ["en", "en-US", "en-GB"]:
            entries = source.get(lang, [])
            texts   = [
                e.get("text", "").strip()
                for e in entries
                if isinstance(e, dict) and "url" not in e and e.get("text")
            ]
            result = " ".join(texts).strip()
            if result:
                return result
    return None


# ── ASSEMBLYAI STT ────────────────────────────────────────────────

def _download_audio(url: str, output_path: str) -> bool:
    cmd = [
        "yt-dlp", "--quiet", "--no-warnings",
        "-x", "--audio-format", "mp3",
        "--audio-quality", "5",
        "--format", "bestaudio/best",
        "-o", output_path,
    ]

    proxy_url = getattr(settings, "proxy_url", "") or ""
    if proxy_url:
        cmd += ["--proxy", proxy_url]

    cookie_path = getattr(settings, "instagram_cookies_path", "") or ""
    if cookie_path and os.path.exists(cookie_path):
        cmd += ["--cookies", cookie_path]

    cmd.append(url)

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        return result.returncode == 0 and os.path.exists(output_path)
    except Exception as e:
        print(f"[PRISM] IG audio download: {type(e).__name__}: {str(e)[:100]}")
        return False


def _transcribe_assemblyai(audio_path: str) -> str | None:
    try:
        import assemblyai as aai
        api_key = getattr(settings, "assemblyai_api_key", "") or ""
        if not api_key:
            return None
        aai.settings.api_key = api_key
        transcriber = aai.Transcriber()
        transcript  = transcriber.transcribe(audio_path)
        if transcript.status == aai.TranscriptStatus.completed and transcript.text:
            text = transcript.text.strip()
            print(f"[PRISM] IG transcript — assemblyai_stt | {len(text)} chars")
            return text
        print(f"[PRISM] AssemblyAI error: {transcript.error}")
        return None
    except Exception as e:
        print(f"[PRISM] AssemblyAI exception: {e}")
        return None


# ── METADATA FALLBACK TEXT ────────────────────────────────────────

def _metadata_to_text(info: dict) -> str:
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


# ── RESPONSE BUILDER ─────────────────────────────────────────────

def _build_response(
    url: str, info: dict, transcript: str, transcript_source: str
) -> dict:
    views    = info.get("view_count") or 0
    likes    = info.get("like_count") or 0
    comments = info.get("comment_count") or 0

    hashtags    = info.get("tags") or []
    description = info.get("description", "")
    if description:
        hashtags = list(set(hashtags + re.findall(r"#\w+", description)))

    eng_rate    = round((likes + comments) / views * 100, 4) if views > 0 else 0.0
    webpage_url = info.get("webpage_url", url)
    platform    = "youtube" if ("youtube.com" in webpage_url or "youtu.be" in webpage_url) else "instagram"

    title = (info.get("title") or info.get("description", "")[:80] or "Instagram Reel")

    print(f"[PRISM] IG  — source: {transcript_source} | chars: {len(transcript)}")

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


# ── MAIN ENTRY ────────────────────────────────────────────────────

def get_instagram_data(url: str, manual_transcript: str | None = None) -> dict:
    """
    Full pipeline — never crashes, always returns a usable payload.

    Priority:
      0. Manual paste (if provided by user)
      1. Supadata API (cloud-safe, IP-block proof)
      2. Inline captions via yt-dlp metadata
      3. AssemblyAI STT on downloaded audio
      4. Metadata text fallback
      5. Minimal placeholder (absolute last resort)
    """
    # ── Priority 0: Manual paste ──────────────────────────────────
    if manual_transcript and manual_transcript.strip():
        info = _get_metadata_subprocess(url) or {}
        return _build_response(url, info, manual_transcript.strip(), "manual_paste")

    # ── Get metadata (best-effort, non-blocking) ──────────────────
    info = _get_metadata_subprocess(url) or {}

    # ── Priority 1: Supadata API ──────────────────────────────────
    transcript = _transcribe_via_supadata(url)
    if transcript:
        return _build_response(url, info, transcript, "supadata_api")

    # ── Priority 2: Inline captions ──────────────────────────────
    if info:
        captions = _extract_inline_captions(info)
        if captions:
            print(f"[PRISM] IG transcript — inline_captions | {len(captions)} chars")
            return _build_response(url, info, captions, "inline_captions")

    # ── Priority 3: AssemblyAI STT ───────────────────────────────
    assemblyai_key = getattr(settings, "assemblyai_api_key", "") or ""
    if assemblyai_key:
        with tempfile.TemporaryDirectory() as tmpdir:
            audio_path = os.path.join(tmpdir, "audio.mp3")
            if _download_audio(url, audio_path):
                transcript = _transcribe_assemblyai(audio_path)
                if transcript:
                    return _build_response(url, info, transcript, "assemblyai_stt")

    # ── Priority 4: Metadata text ─────────────────────────────────
    if info:
        fallback_text = _metadata_to_text(info)
        if fallback_text:
            return _build_response(url, info, fallback_text, "metadata_fallback")

    # ── Priority 5: Absolute last resort — never 422 ─────────────
    print(f"[PRISM WARNING] All pipelines exhausted for {url} — using placeholder")
    placeholder = (
        f"Instagram Reel: {url}\n"
        f"Transcript unavailable — all extraction methods blocked by platform.\n"
        f"Use the manual paste feature to provide transcript content."
    )
    return _build_response(url, {}, placeholder, "pipeline_exhausted")
