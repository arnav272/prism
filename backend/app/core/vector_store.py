"""
PRISM Analytics — Qdrant Vector Store
Hardened for Qdrant Cloud: creates payload indexes for session_id and
video_id so Filter() queries never return 400 Bad Request.
"""
from functools import lru_cache
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams,
    PointStruct, Filter, FieldCondition, MatchValue,
    PayloadSchemaType,
)
from app.core.config import get_settings
from app.core.embeddings import embed_texts, embed_query
import uuid

settings = get_settings()

VECTOR_DIM = 3072  # gemini-embedding-001 output dimensions


@lru_cache(maxsize=1)
def get_qdrant_client() -> QdrantClient:
    """
    Singleton Qdrant client.
    Uses cloud URL+key if configured, falls back to local Docker.
    """
    if settings.qdrant_url and settings.qdrant_url.strip():
        return QdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key or None,
        )
    return QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)


def ensure_collection():
    """
    Create collection if missing. Always ensure payload indexes exist.
    Qdrant Cloud requires explicit indexes for Filter() fields — without
    them, client.search() returns HTTP 400 Bad Request.
    """
    client = get_qdrant_client()
    existing = [c.name for c in client.get_collections().collections]

    if settings.qdrant_collection not in existing:
        client.create_collection(
            collection_name=settings.qdrant_collection,
            vectors_config=VectorParams(size=VECTOR_DIM, distance=Distance.COSINE),
        )

    # Always ensure indexes exist — safe to call even if already created
    _ensure_payload_indexes(client)


def _ensure_payload_indexes(client: QdrantClient):
    """
    Create keyword indexes on session_id and video_id.
    Required for Qdrant Cloud strict filtering. Idempotent.
    """
    for field_name in ["session_id", "video_id"]:
        try:
            client.create_payload_index(
                collection_name=settings.qdrant_collection,
                field_name=field_name,
                field_schema=PayloadSchemaType.KEYWORD,
            )
        except Exception:
            # Index already exists — safe to ignore
            pass


def upsert_chunks(chunks: list[dict], session_id: str):
    """
    Embed and upsert transcript chunks into Qdrant.
    Each chunk payload includes session_id and video_id for filtered search.
    """
    ensure_collection()
    client = get_qdrant_client()

    if not chunks:
        return 0

    texts   = [c["text"] for c in chunks]
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
    top_k: int = 6,
    video_id_filter: str | None = None,
) -> list[dict]:
    """
    Semantic similarity search scoped to a session.
    Payload indexes on session_id and video_id prevent HTTP 400 errors.
    """
    ensure_collection()
    client = get_qdrant_client()

    query_vector = embed_query(query)

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
