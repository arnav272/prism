"""
PRISM Analytics — Ingest Route
POST /api/v1/ingest
Accepts YouTube + Instagram URLs, runs full pipeline.
"""
import asyncio
from fastapi import APIRouter, HTTPException
from pydantic import ValidationError
import traceback

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
    except ValidationError as pydantic_error:
        # CRITICAL DEBUG LAYER: Captures and isolates the exact property breaking the 422 schema
        print("\n" + "="*60)
        print("[PRISM VALIDATION ERROR]: Outbound data mismatch on ingest response models!")
        print(pydantic_error.json(indent=2))
        print("="*60 + "\n")
        raise HTTPException(
            status_code=422,
            detail=pydantic_error.errors()
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        print(f"[PRISM INGEST PIPELINE CRASH]: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Ingest failed: {e}")