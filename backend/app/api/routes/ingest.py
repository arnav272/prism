"""
PRISM Analytics — Ingest Route
POST /api/v1/ingest
Accepts YouTube + Instagram URLs, runs full pipeline.
"""
import asyncio
from fastapi import APIRouter, HTTPException
from app.models.schemas import IngestRequest, IngestResponse
from app.services.ingest_service import run_ingest

router = APIRouter()


@router.post("/ingest", response_model=IngestResponse)
async def ingest_videos(body: IngestRequest):
    """
    Trigger full ingest pipeline for a YouTube + Instagram pair.
    Returns session_id and metadata for both videos.
    Use session_id in all subsequent /chat requests.
    """
    try:
        # Run blocking ingest in thread pool (keeps event loop free)
        result = await asyncio.get_event_loop().run_in_executor(
            None, run_ingest, body.youtube_url, body.instagram_url
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingest failed: {e}")
