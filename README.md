# PRISM Analytics

> Cross-platform RAG chatbot for comparative content intelligence — YouTube vs Instagram.

Built for the technical screening challenge. Designed to scale to **1,000 creators/day** at **$0 infrastructure cost** during development.

---

## Architecture Overview

```
User (React Frontend)
        │
        ▼
   FastAPI Backend
        │
   ┌────┴────────────────┐
   │                     │
LLM Router          Qdrant (local)
   │                     │
   ├── Gemini 1.5 Flash   │◄── all-MiniLM-L6-v2
   └── Groq Llama 3.1 ──►│    (HuggingFace, CPU)
                         │
              youtube-transcript-api
              yt-dlp (cookie mode for IG)
```

### Why This Stack?

| Component | Choice | Reason |
|---|---|---|
| Backend | FastAPI | Async-native, SSE streaming built-in |
| Vector DB | Qdrant (Docker) | Concurrent-safe, persists to disk, free cloud tier for prod |
| Embeddings | all-MiniLM-L6-v2 | 384-dim, ~80ms CPU, $0 forever |
| LLM | Gemini 1.5 Flash + Groq | Combined 15,900 req/day free tier |
| Transcripts | youtube-transcript-api | Stable, uses YT's own caption endpoint |
| IG Scrape | yt-dlp + cookies | Only viable free option; proxy needed at prod scale |

### LLM Load-Balancing Strategy

Requests route to Gemini first. If Gemini hits its RPM window (14 RPM tracked proactively) or throws 5xx errors (circuit breaker after 3 consecutive failures), traffic seamlessly falls over to Groq/Llama 3.1. Combined capacity: **~15,900 requests/day free**.

At 1,000 creators × 5 chat turns = 5,000 LLM calls/day. **3x headroom.**

### What Breaks at 10,000 Users?

- Qdrant: move from local Docker to Qdrant Cloud (free 1GB tier → paid)
- Embeddings: swap CPU inference for a batched GPU worker
- LLM: add GPT-4o Mini ($0.15/1M tokens) as a third provider
- Instagram: requires proxy rotation (~$15/month, Bright Data)

---

## Local Setup

### Prerequisites
- Python 3.11+
- Docker Desktop
- Node.js 20+

### 1. Clone & configure
```bash
git clone https://github.com/YOUR_USERNAME/prism-analytics
cd prism-analytics

cp backend/.env.example backend/.env
# Fill in GEMINI_API_KEY and GROQ_API_KEY
```

### 2. Start Qdrant
```bash
cd docker && docker compose up -d
# Dashboard: http://localhost:6333/dashboard
```

### 3. Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
# Docs: http://localhost:8000/docs
```

### 4. Frontend
```bash
cd frontend
npm install
npm run dev
# App: http://localhost:3000
```

---

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/ingest` | Submit YouTube + Instagram URLs |
| POST | `/api/v1/chat` | Chat with streaming SSE response |
| GET | `/api/v1/metadata/{session_id}` | Fetch video metadata |
| GET | `/health` | Service health check |

---

## Chunking Strategy

- **Chunk size:** 512 words (~2,048 chars)
- **Overlap:** 64 words (prevents context loss at boundaries)
- **Tagging:** every chunk carries `video_id` (A or B) + `platform`
- **Why word-boundary vs character:** avoids mid-word splits that degrade embedding quality

---

## Trade-offs & Honest Limitations

1. **Instagram scraping is fragile.** `yt-dlp` with session cookies works for dev. Production requires proxy rotation (Bright Data ~$15/month) or an official Instagram Graph API key.
2. **Groq answer quality dips** on deep analytical questions vs Gemini. Logged in responses via `model_used` field.
3. **Qdrant local storage** is single-node. At 10K+ users, migrate to Qdrant Cloud or Weaviate cluster.

---

*Built by [Your Name] — every design decision here is one I can defend on a call.*
