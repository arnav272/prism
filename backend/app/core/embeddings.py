"""
PRISM Analytics — Embedding Engine
Uses Google Gemini text-embedding-004 via REST (not gRPC).
gRPC transport deadlocks on macOS Python 3.12 with uvicorn.
REST transport is equally fast for our batch sizes and never hangs.
"""
import os
import requests
from functools import lru_cache
from app.core.config import get_settings

settings = get_settings()

EMBEDDING_DIM = 768  # text-embedding-004 output dimension


def _call_gemini_embed(texts: list[str], task_type: str) -> list[list[float]]:
    """
    Direct REST call to Gemini embedding endpoint.
    Bypasses gRPC entirely — no deadlock, no event loop conflict.
    """
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/"
        f"models/gemini-embedding-001:batchEmbedContents"
        f"?key={settings.gemini_api_key}"
    )

    requests_payload = [
        {
            "model": "models/gemini-embedding-001",
            "content": {"parts": [{"text": t}]},
            "taskType": task_type,
        }
        for t in texts
    ]

    response = requests.post(
        url,
        json={"requests": requests_payload},
        timeout=30,
    )

    if response.status_code != 200:
        raise ValueError(
            f"Gemini embedding API error {response.status_code}: {response.text}"
        )

    data = response.json()
    return [item["values"] for item in data["embeddings"]]


def embed_texts(texts: list[str]) -> list[list[float]]:
    """
    Batch-embed transcript chunks.
    task_type RETRIEVAL_DOCUMENT — optimised for indexing.
    Returns list of 768-dim float vectors.
    """
    return _call_gemini_embed(texts, "RETRIEVAL_DOCUMENT")


def embed_query(text: str) -> list[float]:
    """
    Embed a single search query.
    task_type RETRIEVAL_QUERY — optimised for search.
    Returns single 768-dim float vector.
    """
    return _call_gemini_embed([text], "RETRIEVAL_QUERY")[0]