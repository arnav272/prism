"""
PRISM Analytics — Metadata + Health Routes
GET /api/v1/status         → LLM router status
GET /api/v1/health/full    → Detailed system health
"""
from fastapi import APIRouter
from app.core.llm_router import get_router_status
from app.core.vector_store import get_qdrant_client
from app.core.config import get_settings

router = APIRouter()
settings = get_settings()


@router.get("/status")
async def get_status():
    """Returns current rate limiter + circuit breaker state for both LLMs."""
    return get_router_status()


@router.get("/health/full")
async def full_health():
    """Detailed health check — Qdrant, embedding model, LLM providers."""
    health = {}

    # Qdrant
    try:
        client = get_qdrant_client()
        collections = client.get_collections()
        health["qdrant"] = f"ok — {len(collections.collections)} collection(s)"
    except Exception as e:
        health["qdrant"] = f"error: {e}"

    # LLM keys present
    health["gemini_key_set"] = bool(settings.gemini_api_key)
    health["groq_key_set"]   = bool(settings.groq_api_key)
    health["embedding_model"] = settings.embedding_model
    health["router"] = get_router_status()

    return health
