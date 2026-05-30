"""
PRISM Analytics — RAG Service
LangChain-powered retrieval-augmented generation with:
  - Session-scoped vector retrieval from Qdrant
  - Dual-provider LLM routing (Gemini → Groq fallback)
  - Streaming token output
  - Source citation per chunk
  - Conversation memory across turns
"""
from typing import AsyncGenerator
from langchain.schema import HumanMessage, SystemMessage, AIMessage
from app.core.vector_store import similarity_search
from app.core.llm_router import stream_llm_response
from app.models.schemas import SourceChunk

SYSTEM_PROMPT = """You are PRISM, an expert content analytics assistant.
You analyze social media video content across YouTube and Instagram.

You have access to transcripts and metadata from two videos:
- Video A: YouTube
- Video B: Instagram Reel

When answering:
1. Always cite which video (A or B) your insight comes from.
2. Be specific — reference actual content from the transcripts.
3. For engagement comparisons, use the exact metrics provided.
4. If asked for improvements, be actionable and specific.
5. Keep answers concise but complete.

Context from video transcripts will be provided with each question.
"""


def _build_context_block(chunks: list[dict]) -> str:
    """Format retrieved chunks into a readable context block for the prompt."""
    if not chunks:
        return "No relevant transcript context found."

    lines = []
    for chunk in chunks:
        lines.append(
            f"[Video {chunk['video_id']} | {chunk['platform']} | "
            f"Chunk {chunk['chunk_index']} | Score: {chunk['score']}]\n"
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
    Assemble the full message list for the LLM:
      [SystemMessage, ...history, HumanMessage(context + query)]
    """
    messages = [SystemMessage(content=SYSTEM_PROMPT)]

    # Inject metadata summary if provided (engagement rates, creators, etc.)
    if metadata_summary:
        messages.append(
            SystemMessage(content=f"Video Metadata Summary:\n{metadata_summary}")
        )

    # Conversation history (last 6 turns to stay within context window)
    for turn in history[-6:]:
        if turn["role"] == "user":
            messages.append(HumanMessage(content=turn["content"]))
        elif turn["role"] == "assistant":
            messages.append(AIMessage(content=turn["content"]))

    # Current question with retrieved context
    grounded_query = (
        f"Relevant transcript excerpts:\n\n{context}\n\n"
        f"Question: {user_query}"
    )
    messages.append(HumanMessage(content=grounded_query))

    return messages


async def stream_rag_response(
    query: str,
    session_id: str,
    history: list[dict],
    metadata_summary: str = "",
    top_k: int = 5,
) -> AsyncGenerator[dict, None]:
    """
    Full RAG pipeline as an async generator. Yields:
      {"type": "sources",  "data": list[SourceChunk]}
      {"type": "token",    "content": str}
      {"type": "done",     "model": str}
      {"type": "error",    "content": str}

    Sources are emitted first so the frontend can render citations
    while the answer is still streaming.
    """
    # ── Retrieval ──────────────────────────
    chunks = similarity_search(
        query=query,
        session_id=session_id,
        top_k=top_k,
    )

    # Emit sources immediately (frontend renders while answer streams)
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

    # ── Augmentation ──────────────────────
    context = _build_context_block(chunks)
    messages = _build_messages(query, context, history, metadata_summary)

    # ── Generation (streaming) ─────────────
    async for event in stream_llm_response(messages):
        yield event
