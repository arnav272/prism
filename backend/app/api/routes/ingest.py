import asyncio
from fastapi import APIRouter, HTTPException
from app.models.schemas import IngestRequest, IngestResponse
from app.services.ingest_service import run_ingest

router = APIRouter()

@router.post("/ingest", response_model=IngestResponse)
async def ingest_videos(body: IngestRequest):
    try:
        result = await asyncio.wait_for(
            asyncio.get_event_loop().run_in_executor(
                None,
                lambda: run_ingest(
                    body.youtube_url,
                    body.instagram_url,
                    body.manual_transcript_b,
                )
            ),
            timeout=90.0  # 90 second max — prevents 502 on slow pipelines
        )
        return result
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=504,
            detail="Ingest timed out. Try a different Instagram URL or use the manual paste option."
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingest failed: {str(e)}")