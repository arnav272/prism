"""
PRISM Analytics — Embedding Engine
Wraps HuggingFace all-MiniLM-L6-v2 for local, zero-cost embeddings.
Model loads once at startup and is reused across all requests.
"""
from functools import lru_cache
from sentence_transformers import SentenceTransformer
from langchain_huggingface import HuggingFaceEmbeddings
from app.core.config import get_settings

settings = get_settings()


@lru_cache(maxsize=1)
def get_embedding_model() -> HuggingFaceEmbeddings:
    """
    Singleton embedding model.
    Loaded once on first call, cached in memory for the process lifetime.
    ~80ms per encode on CPU. 384-dim output vectors.
    """
    return HuggingFaceEmbeddings(
        model_name=settings.embedding_model,
        model_kwargs={"device": "cpu"},
        encode_kwargs={
            "normalize_embeddings": True,   # cosine similarity ready
            "batch_size": 32,
        },
    )


def embed_texts(texts: list[str]) -> list[list[float]]:
    """
    Batch-embed a list of strings.
    Returns list of 384-dim float vectors.
    """
    model = get_embedding_model()
    return model.embed_documents(texts)


def embed_query(text: str) -> list[float]:
    """Embed a single query string for similarity search."""
    model = get_embedding_model()
    return model.embed_query(text)
