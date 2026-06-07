"""
PRISM Analytics — Metadata + Health Routes
GET /api/v1/status              → LLM router status
GET /api/v1/health/full         → Detailed system health
GET /api/v1/debug/transcript/{video_id} → Transcript availability check
"""
from fastapi import APIRouter
from app.core.llm_router import get_router_status
from app.core.vector_store import get_qdrant_client
from app.core.config import get_settings

router = APIRouter()
settings = get_settings()


@router.get("/status")
async def get_status():
    return get_router_status()


@router.get("/health/full")
async def full_health():
    health = {}

    try:
        client = get_qdrant_client()
        collections = client.get_collections()
        health["qdrant"] = f"ok — {len(collections.collections)} collection(s)"
    except Exception as e:
        health["qdrant"] = f"error: {e}"

    health["gemini_key_set"]   = bool(settings.gemini_api_key)
    health["groq_key_set"]     = bool(settings.groq_api_key)
    health["youtube_api_key_set"] = bool(getattr(settings, "youtube_api_key", ""))
    health["assemblyai_key_set"]  = bool(getattr(settings, "assemblyai_api_key", ""))
    health["embedding_model"]  = getattr(settings, "gemini_embedding_model", "unknown")
    health["router"]           = get_router_status()
    health["supadata_key_set"] = bool(getattr(settings, "supadata_api_key", ""))

    return health


@router.get("/debug/transcript/{video_id}")
async def debug_transcript(video_id: str):
    """
    Check which transcript tracks are available for a YouTube video.
    Use to diagnose why youtube-transcript-api falls back to metadata.
    Hit: /api/v1/debug/transcript/dQw4w9WgXcQ
    """
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

        available = []
        for t in transcript_list:
            available.append({
                "language":      t.language,
                "language_code": t.language_code,
                "is_generated":  t.is_generated,
                "is_translatable": t.is_translatable,
            })

        # Also attempt to actually fetch English
        fetch_result = None
        try:
            t       = transcript_list.find_generated_transcript(["en", "en-US"])
            entries = t.fetch()
            text    = " ".join(e["text"] for e in entries).strip()
            fetch_result = {
                "status": "success",
                "chars":  len(text),
                "preview": text[:200],
            }
        except Exception as fe:
            fetch_result = {"status": "failed", "error": str(fe)}

        return {
            "status":       "ok",
            "video_id":     video_id,
            "available":    available,
            "fetch_attempt": fetch_result,
        }

    except Exception as e:
        return {
            "status":    "error",
            "video_id":  video_id,
            "error":     str(e),
            "type":      type(e).__name__,
        }