# ─────────────────────────────────────────────────────
#  PRISM Analytics — Production Dockerfile
#  Target: Render free tier (512MB RAM, shared CPU)
#
#  Key decisions:
#  - python:3.11-slim  → smallest stable base (~45MB vs ~900MB full)
#  - No HuggingFace model download (switched to Gemini Embeddings API)
#  - Non-root user for security (Render best practice)
#  - Single worker + async handles concurrent requests fine at free tier
# ─────────────────────────────────────────────────────

FROM python:3.11-slim

# ── System deps ──────────────────────────────────────
# ffmpeg needed by yt-dlp for some media processing
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# ── Non-root user (Render security requirement) ──────
RUN useradd -m -u 1000 prism
WORKDIR /app

# ── Install Python deps first (layer cache friendly) ─
# Copy requirements before source so pip layer is cached
# unless requirements.txt actually changes
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# ── Copy application source ──────────────────────────
COPY app/ ./app/

# ── Switch to non-root ───────────────────────────────
RUN chown -R prism:prism /app
USER prism

# ── Runtime config ───────────────────────────────────
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000

EXPOSE 8000

# ── Health check (Render uses this to confirm startup) ─
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# ── Start command ────────────────────────────────────
# Single uvicorn worker is correct for Render free tier:
# - 512MB RAM can't support multiple workers safely
# - FastAPI's async handles concurrent I/O without threads
CMD uvicorn app.main:app \
    --host 0.0.0.0 \
    --port ${PORT} \
    --workers 1 \
    --log-level info