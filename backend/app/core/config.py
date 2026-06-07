"""
PRISM Analytics — Central Configuration
"""
try:
    # Prefer pydantic v2 separate settings package when available
    from pydantic_settings import BaseSettings
except Exception:
    # Fallback to pydantic's BaseSettings for environments without pydantic_settings
    from pydantic import BaseSettings
from pydantic import Field
from functools import lru_cache


class Settings(BaseSettings):
    # App
    app_env: str = Field(default="development")
    log_level: str = Field(default="INFO")
    cors_origins: str = Field(default="http://localhost:3000")

    # LLM Providers
    gemini_api_key: str = Field(default="")
    groq_api_key: str = Field(default="")
    primary_llm: str = Field(default="gemini")
    gemini_model: str = Field(default="gemini-2.5-flash")
    groq_model: str = Field(default="llama-3.3-70b-versatile")

    # YouTube Data API v3 Layer
    youtube_api_key: str = Field(default="")
    supadata_api_key: str = Field(default="")
    # ScrapeOps Proxy Layer
    scrapeops_api_key: str | None = Field(default=None)
    proxy_url: str = Field(default="")
    # Rate Limits
    gemini_rpm_limit: int = Field(default=14)
    groq_rpm_limit: int = Field(default=28)
    gemini_daily_limit: int = Field(default=1400)
    groq_daily_limit: int = Field(default=14000)

    # Circuit Breaker
    circuit_breaker_threshold: int = Field(default=3)
    circuit_breaker_timeout: int = Field(default=300)

    # Qdrant
    qdrant_url: str = Field(default="")
    qdrant_api_key: str = Field(default="")
    qdrant_host: str = Field(default="localhost")
    qdrant_port: int = Field(default=6333)
    qdrant_collection: str = Field(default="prism_chunks")

    # Embeddings
    gemini_embedding_model: str = Field(default="models/gemini-embedding-001")

    # Chunking
    chunk_size: int = Field(default=400)
    chunk_overlap: int = Field(default=80)

    # Transcription
    assemblyai_api_key: str = Field(default="")
    instagram_cookies_path: str = Field(default="./cookies/instagram.txt")

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "case_sensitive": False}


@lru_cache()
def get_settings() -> Settings:
    return Settings()