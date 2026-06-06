"""
PRISM Analytics — Qdrant Vector Store
Handles collection creation, chunk upsert, and similarity search.
Each chunk is stored with full metadata payload for citation rendering.
"""
from functools import lru_cache
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams,
    PointStruct, Filter, FieldCondition, MatchValue,
)
from app.core.config import get_settings
from app.core.embeddings import embed_texts, embed_query
import uuid

settings = get_settings()

VECTOR_DIM = 3072  # all-MiniLM-L6-v2 output dimension


@lru_cache(maxsize=1)
def get_qdrant_client() -> QdrantClient:
    """
    Robust initialization for QdrantClient.
    Gracefully shifts between cloud clusters (Render) and local development (MacBook).
    """
    # 1. Check for explicit full cloud URL first (Render environment)
    qdrant_url = getattr(settings, "qdrant_url", None)
    api_key = getattr(settings, "qdrant_api_key", None)

    if qdrant_url and qdrant_url.strip():
        print(f"[PRISM] Vector Store connecting via Cloud Cluster URL: {qdrant_url}")
        return QdrantClient(url=qdrant_url, api_key=api_key)
        
    # 2. Fallback check if host string itself holds an absolute cloud endpoint
    if api_key and api_key.strip() and settings.qdrant_host and "qdrant" in settings.qdrant_host:
        url_target = settings.qdrant_host if settings.qdrant_host.startswith("http") else f"https://{settings.qdrant_host}"
        print(f"[PRISM] Vector Store routing cloud host endpoint via URL: {url_target}")
        return QdrantClient(url=url_target, api_key=api_key)

    # 3. Standard fallback configuration pattern for local development setups (localhost)
    print(f"[PRISM] Vector Store connecting locally to development host: {settings.qdrant_host}:{settings.qdrant_port}")
    return QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)


def ensure_collection():
    """
    Create the Qdrant collection if it doesn't exist.
    Safe to call on every startup.
    """
    client = get_qdrant_client()
    existing = [c.name for c in client.get_collections().collections]

    if settings.qdrant_collection not in existing:
        client.create_collection(
            collection_name=settings.qdrant_collection,
            vectors_config=VectorParams(size=VECTOR_DIM, distance=Distance.COSINE),
        )


def upsert_chunks(chunks: list[dict], session_id: str):
    """
    Embed and upsert a list of transcript chunks into Qdrant.

    Each chunk dict must have:
      text, chunk_index, video_id, platform, char_start, char_end

    Payload stored per point (for citation in chat responses):
      text, chunk_index, video_id, platform, session_id
    """
    ensure_collection()
    client = get_qdrant_client()

    texts = [c["text"] for c in chunks]
    vectors = embed_texts(texts)

    points = [
        PointStruct(
            id=str(uuid.uuid4()),
            vector=vector,
            payload={
                "text":        chunk["text"],
                "chunk_index": chunk["chunk_index"],
                "video_id":    chunk["video_id"],
                "platform":    chunk["platform"],
                "session_id":  session_id,
                "char_start":  chunk.get("char_start", 0),
                "char_end":    chunk.get("char_end", 0),
            },
        )
        for chunk, vector in zip(chunks, vectors)
    ]

    client.upsert(collection_name=settings.qdrant_collection, points=points)
    return len(points)


def similarity_search(
    query: str,
    session_id: str,
    top_k: int = 5,
    video_id_filter: str | None = None,
) -> list[dict]:
    """
    Search for the most relevant chunks for a given query.
    Optionally filter by video_id ("A" or "B").

    Returns list of dicts with text, score, and full metadata.
    """
    ensure_collection()
    client = get_qdrant_client()

    query_vector = embed_query(query)

    # Build filter: always scope to session, optionally to video_id
    must_conditions = [
        FieldCondition(key="session_id", match=MatchValue(value=session_id))
    ]
    if video_id_filter:
        must_conditions.append(
            FieldCondition(key="video_id", match=MatchValue(value=video_id_filter))
        )

    results = client.search(
        collection_name=settings.qdrant_collection,
        query_vector=query_vector,
        query_filter=Filter(must=must_conditions),
        limit=top_k,
        with_payload=True,
    )

    return [
        {
            "text":        r.payload["text"],
            "score":       round(r.score, 4),
            "chunk_index": r.payload["chunk_index"],
            "video_id":    r.payload["video_id"],
            "platform":    r.payload["platform"],
        }
        for r in results
    ]