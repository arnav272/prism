"""
PRISM Analytics — Pre-flight Health Check
Run before starting the server to verify all dependencies.
Usage: python scripts/health_check.py
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

def check(label: str, fn):
    try:
        fn()
        print(f"  ✅  {label}")
        return True
    except Exception as e:
        print(f"  ❌  {label}: {e}")
        return False

results = []

# 1. Qdrant reachable
def check_qdrant():
    from qdrant_client import QdrantClient
    client = QdrantClient(host="localhost", port=6333)
    client.get_collections()
results.append(check("Qdrant (localhost:6333)", check_qdrant))

# 2. HuggingFace model loads
def check_embeddings():
    from sentence_transformers import SentenceTransformer
    m = SentenceTransformer("all-MiniLM-L6-v2")
    m.encode(["test"])
results.append(check("Embedding model (all-MiniLM-L6-v2)", check_embeddings))

# 3. Gemini API key present
def check_gemini():
    key = os.getenv("GEMINI_API_KEY", "")
    assert key and key != "your_gemini_api_key_here", "GEMINI_API_KEY not set"
results.append(check("Gemini API key in env", check_gemini))

# 4. Groq API key present
def check_groq():
    key = os.getenv("GROQ_API_KEY", "")
    assert key and key != "your_groq_api_key_here", "GROQ_API_KEY not set"
results.append(check("Groq API key in env", check_groq))

# 5. yt-dlp installed
def check_ytdlp():
    import yt_dlp
results.append(check("yt-dlp installed", check_ytdlp))

# 6. youtube-transcript-api installed
def check_yta():
    import youtube_transcript_api
results.append(check("youtube-transcript-api installed", check_yta))

print()
if all(results):
    print("🚀 All checks passed. Ready to run: uvicorn app.main:app --reload")
else:
    failed = results.count(False)
    print(f"⚠️  {failed} check(s) failed. Fix above before starting the server.")
    sys.exit(1)
