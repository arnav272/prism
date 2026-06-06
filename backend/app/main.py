"""
PRISM Analytics — FastAPI Entry Point
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import get_settings
from app.api.routes import ingest, chat, metadata

settings = get_settings()

app = FastAPI(
    title="PRISM Analytics API",
    description="Cross-platform RAG analytics for YouTube + Instagram content",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ingest.router,   prefix="/api/v1", tags=["Ingest"])
app.include_router(chat.router,     prefix="/api/v1", tags=["Chat"])
app.include_router(metadata.router, prefix="/api/v1", tags=["Metadata"])


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok", "service": "PRISM Analytics API", "version": "1.0.0"}
