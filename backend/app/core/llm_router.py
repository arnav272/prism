"""
PRISM Analytics — LLM Router
Smart load-balancer across Gemini 1.5 Flash and Groq/Llama 3.1.

Routing logic:
  1. Check Gemini availability (RPM + daily + circuit breaker)
  2. If available → use Gemini
  3. If not → failover to Groq
  4. If both unavailable → raise with clear message

Streaming-first: yields text tokens as they arrive.
"""
import asyncio
from typing import AsyncGenerator
from app.core.config import get_settings
from app.utils.rate_limiter import gemini_limiter, groq_limiter

settings = get_settings()


def _get_gemini_llm():
    """Build a Gemini 1.5 Flash LangChain LLM instance."""
    from langchain_google_genai import ChatGoogleGenerativeAI
    return ChatGoogleGenerativeAI(
        model=settings.gemini_model,
        google_api_key=settings.gemini_api_key,
        temperature=0.3,
        streaming=True,
    )


def _get_groq_llm():
    """Build a Groq/Llama LangChain LLM instance."""
    from langchain_groq import ChatGroq
    return ChatGroq(
        model=settings.groq_model,
        groq_api_key=settings.groq_api_key,
        temperature=0.3,
        streaming=True,
    )


def get_available_llm() -> tuple:
    """
    Returns (llm_instance, provider_name, limiter).
    Raises RuntimeError if both providers are exhausted.
    """
    if gemini_limiter.is_available():
        return _get_gemini_llm(), "gemini", gemini_limiter

    if groq_limiter.is_available():
        return _get_groq_llm(), "groq", groq_limiter

    status_g = gemini_limiter.get_status()
    status_gr = groq_limiter.get_status()
    raise RuntimeError(
        f"Both LLM providers are unavailable.\n"
        f"Gemini: {status_g}\n"
        f"Groq: {status_gr}"
    )


async def stream_llm_response(
    messages: list,
) -> AsyncGenerator[dict, None]:
    """
    Core streaming generator. Yields dicts:
      {"type": "token",    "content": str}
      {"type": "done",     "model": str}
      {"type": "error",    "content": str}

    Automatically records success/error on the limiter.
    """
    llm, provider, limiter = get_available_llm()
    limiter.record_request()

    try:
        full_response = ""
        async for chunk in llm.astream(messages):
            token = chunk.content
            if token:
                full_response += token
                yield {"type": "token", "content": token}

        limiter.record_success()
        yield {"type": "done", "model": provider}

    except Exception as e:
        limiter.record_error()

        # Attempt failover to the other provider
        other_provider = "groq" if provider == "gemini" else "gemini"
        other_available = groq_limiter.is_available() if provider == "gemini" else gemini_limiter.is_available()

        if other_available:
            yield {"type": "token", "content": ""}  # flush
            fallback_llm = _get_groq_llm() if provider == "gemini" else _get_gemini_llm()
            fallback_limiter = groq_limiter if provider == "gemini" else gemini_limiter
            fallback_limiter.record_request()

            try:
                async for chunk in fallback_llm.astream(messages):
                    token = chunk.content
                    if token:
                        yield {"type": "token", "content": token}

                fallback_limiter.record_success()
                yield {"type": "done", "model": other_provider}

            except Exception as fallback_error:
                fallback_limiter.record_error()
                yield {"type": "error", "content": f"Both providers failed: {fallback_error}"}
        else:
            yield {"type": "error", "content": f"Provider {provider} failed and no fallback available: {e}"}


def get_router_status() -> dict:
    """Returns current rate limit status for both providers."""
    return {
        "gemini": gemini_limiter.get_status(),
        "groq":   groq_limiter.get_status(),
    }
