"""
PRISM Analytics — Transcript Chunker
Splits raw transcript text into overlapping chunks.
Each chunk is tagged with video_id (A or B) for RAG retrieval.
"""
from app.core.config import get_settings

settings = get_settings()


def chunk_transcript(
    transcript: str,
    video_id: str,           # "A" or "B"
    platform: str,           # "youtube" or "instagram"
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> list[dict]:
    """
    Splits transcript into overlapping word-boundary chunks.

    Returns list of dicts:
      {
        "text": str,
        "chunk_index": int,
        "video_id": "A" | "B",
        "platform": str,
        "char_start": int,
        "char_end": int,
      }

    Design note: word-boundary chunking (vs character) avoids
    splitting mid-word, which degrades embedding quality.
    512 tokens / ~4 chars per token ≈ 2048 chars, but we
    chunk by words for cleanliness.
    """
    size = chunk_size or settings.chunk_size
    overlap = chunk_overlap or settings.chunk_overlap

    words = transcript.split()
    chunks = []
    i = 0
    chunk_index = 0

    while i < len(words):
        chunk_words = words[i : i + size]
        chunk_text = " ".join(chunk_words)

        char_start = len(" ".join(words[:i]))
        char_end = char_start + len(chunk_text)

        chunks.append({
            "text": chunk_text,
            "chunk_index": chunk_index,
            "video_id": video_id,
            "platform": platform,
            "char_start": char_start,
            "char_end": char_end,
        })

        i += size - overlap
        chunk_index += 1

    return chunks
