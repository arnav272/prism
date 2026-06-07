"""
PRISM Analytics — Adaptive Transcript Chunker
Dynamically adjusts chunk size based on transcript length.
Short transcripts (metadata fallback) → small chunks → more vectors.
Long transcripts (real captions) → larger chunks → richer context.
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

    words   = transcript.split()
    n_words = len(words)

    if not words:
        return [{
            "text":        f"[No content available for {platform} video]",
            "chunk_index": 0,
            "video_id":    video_id,
            "platform":    platform,
            "char_start":  0,
            "char_end":    0,
        }]

    # Adaptive sizing based on transcript length
    if chunk_size and chunk_overlap:
        size    = chunk_size
        overlap = chunk_overlap
    elif n_words <= 100:
        size, overlap = 20, 4       # Very short → 5-8 chunks
    elif n_words <= 300:
        size, overlap = 40, 8       # Short → 8-12 chunks
    elif n_words <= 600:
        size, overlap = 60, 12      # Medium → 10-15 chunks
    else:
        size, overlap = 120, 24     # Long → 15-25 chunks

    chunks = []
    i      = 0
    idx    = 0

    while i < len(words):
        chunk_words = words[i: i + size]
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