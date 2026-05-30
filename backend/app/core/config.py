"""
PRISM Analytics — Central Configuration
Loads all settings from .env via pydantic-settings.
Single source of truth for the entire backend.
"""
from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache


class Settings(BaseSettings):
    # ── App ──────────────────────────────
    app_env: str = Field(default="development")
    log_level: str = Field(default="INFO")
    cors_origins: str = Field(default="http://localhost:3000")

    # ── LLM Providers ────────────────────
    gemini_api_key: str = Field(default="")
    groq_api_key: str = Field(default="")
    primary_llm: str = Field(default="gemini")
    gemini_model: str = Field(default="gemini-1.5-flash")
    groq_model: str = Field(default="llama-3.1-70b-versatile")

    # ── Rate Limits (buffered) ────────────
    gemini_rpm_limit: int = Field(default=14)
    groq_rpm_limit: int = Field(default=28)
    gemini_daily_limit: int = Field(default=1400)
    groq_daily_limit: int = Field(default=14000)

    # ── Circuit Breaker ───────────────────
    circuit_breaker_threshold: int = Field(default=3)
    circuit_breaker_timeout: int = Field(default=300)

    # ── Qdrant ───────────────────────────
    qdrant_host: str = Field(default="localhost")
    qdrant_port: int = Field(default=6333)
    qdrant_collection: str = Field(default="prism_chunks")

    # ── Embeddings ───────────────────────
    embedding_model: str = Field(default="all-MiniLM-L6-v2")

    # ── Chunking ─────────────────────────
    chunk_size: int = Field(default=512)
    chunk_overlap: int = Field(default=64)

    # ── Instagram ────────────────────────
    instagram_cookies_path: str = Field(default="./cookies/instagram.txt")

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Cached singleton — only reads .env once per process lifetime."""
    return Settings()
