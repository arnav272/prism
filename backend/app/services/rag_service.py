"""
PRISM Analytics — RAG Service
Injects explicit video metadata into every LLM prompt so the model
can always answer engagement/metrics questions, not just transcript ones.
"""
from typing import AsyncGenerator

# Import langchain.schema dynamically to avoid static analysis errors when the
# package is not installed; fall back to lightweight dataclasses otherwise.
try:
    import importlib

    _langchain_schema = importlib.import_module("langchain.schema")
    HumanMessage = getattr(_langchain_schema, "HumanMessage")
    SystemMessage = getattr(_langchain_schema, "SystemMessage")
    AIMessage = getattr(_langchain_schema, "AIMessage")
except Exception:
    # Fallback lightweight message types when langchain is not installed
    from dataclasses import dataclass

    @dataclass
    class HumanMessage:
        content: str

    @dataclass
    class SystemMessage:
        content: str

    @dataclass
    class AIMessage:
        content: str

from app.core.vector_store import similarity_search
from app.core.llm_router import stream_llm_response
from app.models.schemas import SourceChunk

# ── Base system prompt ────────────────────────────────────────────
BASE_SYSTEM_PROMPT = """You are PRISM, an expert content analytics assistant.

You have explicit access to TWO data sources for each video:
1. ENGAGEMENT METRICS — views, likes, comments, engagement rate, follower count, upload date, duration
2. TRANSCRIPT CHUNKS — the actual spoken content from each video

The metrics are injected directly into your context below. Use them precisely when answering analytical questions. Never say you "cannot see" or "don't have access to" engagement data — it is always provided.

Rules:
- Always cite which video (A or B) your insight comes from
- For engagement comparisons, use the EXACT numbers from the metrics block
- For content/hook/transcript analysis, reference the transcript chunks
- Be specific and actionable — vague answers are not acceptable
- If asked for improvements, ground them in the actual data provided
"""


def _build_metrics_block(metadata_summary: str) -> str:
    """Formats the metrics injection block prepended to every prompt."""
    if not metadata_summary:
        return ""
    return f"""
══════════════════════════════════════
VIDEO METRICS — USE THESE FOR ALL ANALYTICAL QUESTIONS
══════════════════════════════════════
{metadata_summary}
══════════════════════════════════════
"""


def _build_context_block(chunks: list[dict]) -> str:
    """Formats retrieved transcript chunks."""
    if not chunks:
        return "No transcript chunks retrieved for this query."
    lines = []
    for chunk in chunks:
        lines.append(
            f"[Video {chunk['video_id']} | {chunk['platform']} | "
            f"Chunk {chunk['chunk_index']} | Relevance: {chunk['score']}]\n"
            f"{chunk['text']}"
        )
    return "\n\n---\n\n".join(lines)


def _build_messages(
    user_query: str,
    context: str,
    history: list[dict],
    metadata_summary: str = "",
) -> list:
    """
    Assembles the full message list:
      SystemMessage (base prompt)
      SystemMessage (metrics block — always injected)
      ...history (last 6 turns)
      HumanMessage (transcript context + query)
    """
    messages = [SystemMessage(content=BASE_SYSTEM_PROMPT)]

    # Always inject metrics as a second system message
    if metadata_summary:
        metrics_block = _build_metrics_block(metadata_summary)
        messages.append(SystemMessage(content=metrics_block))

    # Conversation history (last 6 turns)
    for turn in history[-6:]:
        if turn["role"] == "user":
            messages.append(HumanMessage(content=turn["content"]))
        elif turn["role"] == "assistant":
            messages.append(AIMessage(content=turn["content"]))

    # Current question with retrieved transcript context
    grounded_query = (
        f"RELEVANT TRANSCRIPT EXCERPTS:\n\n{context}\n\n"
        f"USER QUESTION: {user_query}"
    )
    messages.append(HumanMessage(content=grounded_query))
    return messages


async def stream_rag_response(
    query: str,
    session_id: str,
    history: list[dict],
    metadata_summary: str = "",
    top_k: int = 6,
) -> AsyncGenerator[dict, None]:
    """
    Full RAG pipeline. Yields:
      {"type": "sources",  "data": list[SourceChunk]}
      {"type": "token",    "content": str}
      {"type": "done",     "model": str}
      {"type": "error",    "content": str}
    """
    # Retrieval
    chunks = similarity_search(
        query=query,
        session_id=session_id,
        top_k=top_k,
    )

    # Emit sources immediately
    source_models = [
        SourceChunk(
            video_id=c["video_id"],
            platform=c["platform"],
            chunk_text=c["text"],
            chunk_index=c["chunk_index"],
            score=c["score"],
        )
        for c in chunks
    ]
    yield {"type": "sources", "data": [s.model_dump() for s in source_models]}

    # Build context + messages with metrics always injected
    context  = _build_context_block(chunks)
    messages = _build_messages(query, context, history, metadata_summary)

    # Stream from LLM router
    async for event in stream_llm_response(messages):
        yield event
