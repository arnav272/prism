"""
PRISM Analytics — Chat Route (Streaming SSE)
Pulls session metadata summary and injects into every RAG prompt.
"""
import json
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from app.models.schemas import ChatRequest
from app.services.rag_service import stream_rag_response
from app.services.ingest_service import SESSION_METADATA

router = APIRouter()


async def _event_generator(body: ChatRequest):
    history = [{"role": m.role, "content": m.content} for m in body.history]

    # Pull cached metadata for this session — empty string if not found
    metadata_summary = SESSION_METADATA.get(body.session_id, "")

    async for event in stream_rag_response(
        query=body.message,
        session_id=body.session_id,
        history=history,
        metadata_summary=metadata_summary,
    ):
        yield f"data: {json.dumps(event)}\n\n"

    yield "data: [DONE]\n\n"


@router.post("/chat")
async def chat(body: ChatRequest):
    if not body.session_id:
        raise HTTPException(status_code=400, detail="session_id is required")

    return StreamingResponse(
        _event_generator(body),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
