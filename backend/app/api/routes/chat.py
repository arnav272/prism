"""
PRISM Analytics — Chat Route (Streaming SSE)
POST /api/v1/chat
Streams RAG response tokens with source citations.
"""
import json
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from app.models.schemas import ChatRequest
from app.services.rag_service import stream_rag_response

router = APIRouter()


async def _event_generator(body: ChatRequest):
    """Convert RAG stream events to SSE format."""
    history = [{"role": m.role, "content": m.content} for m in body.history]

    async for event in stream_rag_response(
        query=body.message,
        session_id=body.session_id,
        history=history,
    ):
        yield f"data: {json.dumps(event)}\n\n"

    yield "data: [DONE]\n\n"


@router.post("/chat")
async def chat(body: ChatRequest):
    """
    Stream a RAG-grounded answer for a user question.
    Events:
      sources  → list of SourceChunk (emitted first)
      token    → streamed answer text
      done     → model name that answered
      error    → error message
    """
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
