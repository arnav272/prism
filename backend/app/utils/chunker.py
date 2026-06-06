"""
PRISM Analytics — Transcript Chunker
chunk_size=400 words, overlap=80 words.
Produces 15-25 chunks for a typical 3-minute video transcript.
"""
from app.core.config import get_settings

settings = get_settings()


def chunk_transcript(
    transcript: str,
    video_id: str,
    platform: str,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> list[dict]:
    size    = chunk_size    or 400
    overlap = chunk_overlap or 80

    words = transcript.split()

    if not words:
        return [{
            "text":        f"[No content available for {platform} video]",
            "chunk_index": 0,
            "video_id":    video_id,
            "platform":    platform,
            "char_start":  0,
            "char_end":    0,
        }]

    chunks = []
    i = 0
    idx = 0

    while i < len(words):
        chunk_words = words[i : i + size]
        chunk_text  = " ".join(chunk_words)
        char_start  = len(" ".join(words[:i])) + (1 if i > 0 else 0)
        char_end    = char_start + len(chunk_text)

        chunks.append({
            "text":        chunk_text,
            "chunk_index": idx,
            "video_id":    video_id,
            "platform":    platform,
            "char_start":  char_start,
            "char_end":    char_end,
        })

        i   += size - overlap
        idx += 1

    return chunks
