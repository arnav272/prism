"""
PRISM Analytics — Stateful Rate Limiter + Circuit Breaker
Tracks RPM and daily usage per LLM provider in-process memory.
Proactively routes BEFORE hitting 429s, not after.
"""
import time
import threading
from collections import deque
from enum import Enum
from app.core.config import get_settings

settings = get_settings()


class CircuitState(Enum):
    CLOSED = "closed"       # Normal — requests flow through
    OPEN = "open"           # Tripped — requests blocked
    HALF_OPEN = "half_open" # Testing if provider recovered


class ProviderRateLimiter:
    """
    Per-provider rate limiter with:
    - Sliding window RPM tracking
    - Daily request counter
    - Circuit breaker pattern
    """

    def __init__(self, name: str, rpm_limit: int, daily_limit: int):
        self.name = name
        self.rpm_limit = rpm_limit
        self.daily_limit = daily_limit

        self._lock = threading.Lock()
        self._rpm_window: deque[float] = deque()   # timestamps in last 60s
        self._daily_count = 0
        self._daily_reset_time = time.time() + 86400  # reset in 24h

        # Circuit breaker state
        self._circuit_state = CircuitState.CLOSED
        self._consecutive_errors = 0
        self._circuit_opened_at: float | None = None

    def is_available(self) -> bool:
        """Check if this provider can accept a request right now."""
        with self._lock:
            self._reset_daily_if_needed()
            self._prune_rpm_window()

            # Circuit breaker check
            if self._circuit_state == CircuitState.OPEN:
                elapsed = time.time() - self._circuit_opened_at
                if elapsed >= settings.circuit_breaker_timeout:
                    self._circuit_state = CircuitState.HALF_OPEN
                else:
                    return False

            # Capacity checks
            if self._daily_count >= self.daily_limit:
                return False
            if len(self._rpm_window) >= self.rpm_limit:
                return False

            return True

    def record_request(self):
        """Call this when a request is sent to the provider."""
        with self._lock:
            now = time.time()
            self._rpm_window.append(now)
            self._daily_count += 1

    def record_success(self):
        """Call on successful response — resets circuit breaker error count."""
        with self._lock:
            self._consecutive_errors = 0
            if self._circuit_state == CircuitState.HALF_OPEN:
                self._circuit_state = CircuitState.CLOSED

    def record_error(self):
        """Call on provider error — may trip circuit breaker."""
        with self._lock:
            self._consecutive_errors += 1
            if self._consecutive_errors >= settings.circuit_breaker_threshold:
                self._circuit_state = CircuitState.OPEN
                self._circuit_opened_at = time.time()

    def get_status(self) -> dict:
        with self._lock:
            self._prune_rpm_window()
            return {
                "provider": self.name,
                "circuit": self._circuit_state.value,
                "rpm_current": len(self._rpm_window),
                "rpm_limit": self.rpm_limit,
                "daily_current": self._daily_count,
                "daily_limit": self.daily_limit,
            }

    def _prune_rpm_window(self):
        cutoff = time.time() - 60
        while self._rpm_window and self._rpm_window[0] < cutoff:
            self._rpm_window.popleft()

    def _reset_daily_if_needed(self):
        if time.time() >= self._daily_reset_time:
            self._daily_count = 0
            self._daily_reset_time = time.time() + 86400


# ── Singletons — one per provider ────────
gemini_limiter = ProviderRateLimiter(
    name="gemini",
    rpm_limit=settings.gemini_rpm_limit,
    daily_limit=settings.gemini_daily_limit,
)

groq_limiter = ProviderRateLimiter(
    name="groq",
    rpm_limit=settings.groq_rpm_limit,
    daily_limit=settings.groq_daily_limit,
)
