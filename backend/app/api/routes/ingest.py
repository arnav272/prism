"""
PRISM Analytics — Ingest Route
POST /api/v1/ingest
Accepts YouTube + Instagram URLs, runs full pipeline with strict error breakout.
"""
import asyncio
from fastapi import APIRouter, HTTPException
from pydantic import ValidationError
import traceback

from app.models.schemas import IngestRequest, IngestResponse
from app.services.ingest_service import run_ingest

router = APIRouter()


# REMOVED response_model field validation filter from the decorator temporarily 
# so we can trap the parsing structural failure manually inside our try block!
@router.post("/ingest")
async def ingest_videos(body: IngestRequest):
    """
    Trigger full ingest pipeline for a YouTube + Instagram pair.
    Returns session_id and metadata for both videos.
    Use session_id in all subsequent /chat requests.
    """
    try:
        # Run blocking ingest in thread pool (keeps event loop free)
        raw_result = await asyncio.get_event_loop().run_in_executor(
            None, run_ingest, body.youtube_url, body.instagram_url
        )
        
        # FORCE Pydantic to validate the dict here where we can explicitly catch it!
        validated_response = IngestResponse(**raw_result)
        
        return validated_response
        
    except ValidationError as pydantic_error:
        # CRITICAL DEBUG LAYER: This captures the exact field name causing the 422 mismatch
        print("\n" + "🚨 " * 20)
        print("[PRISM SCHEMA VALIDATION ERROR DETECTED]:")
        print(pydantic_error.json(indent=2))
        print("🚨 " * 20 + "\n")
        
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