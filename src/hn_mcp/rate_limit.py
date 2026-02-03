"""Rate limiting for HN API requests.

Implements a sliding window rate limiter to prevent hitting API limits.
Default: 300 requests per minute (matching karanb192/hn-mcp).
"""

import asyncio
import time
from collections import deque
from dataclasses import dataclass, field


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""

    requests_per_minute: int = 300
    burst_allowance: float = 1.2  # Allow 20% burst above limit


@dataclass
class RateLimiter:
    """Sliding window rate limiter for API requests.

    Uses a deque to track request timestamps within the window.
    Thread-safe for async usage via asyncio.Lock.
    """

    config: RateLimitConfig = field(default_factory=RateLimitConfig)
    _timestamps: "deque[float]" = field(default_factory=lambda: deque())
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    @property
    def max_requests(self) -> int:
        """Maximum requests allowed in the window (including burst)."""
        return int(self.config.requests_per_minute * self.config.burst_allowance)

    @property
    def window_seconds(self) -> float:
        """Size of the sliding window in seconds."""
        return 60.0

    async def acquire(self) -> float:
        """Acquire permission to make a request.

        Returns:
            Wait time in seconds (0 if no wait needed).

        Raises:
            RateLimitExceeded: If rate limit is exceeded and cannot wait.
        """
        async with self._lock:
            now = time.monotonic()

            # Remove timestamps outside the window
            cutoff = now - self.window_seconds
            while self._timestamps and self._timestamps[0] < cutoff:
                self._timestamps.popleft()

            # Check if we're at capacity
            if len(self._timestamps) >= self.max_requests:
                # Calculate wait time until oldest request expires
                oldest = self._timestamps[0]
                wait_time = (oldest + self.window_seconds) - now
                if wait_time > 0:
                    return wait_time

            # Record this request
            self._timestamps.append(now)
            return 0.0

    async def wait_and_acquire(self) -> None:
        """Wait if necessary and acquire permission to make a request.

        Uses iteration instead of recursion to avoid stack overflow
        under sustained high load.
        """
        while True:
            wait_time = await self.acquire()
            if wait_time <= 0:
                return
            await asyncio.sleep(wait_time)

    async def stats(self) -> dict[str, int | float]:
        """Get current rate limiter statistics.

        Thread-safe via async lock to prevent data races during iteration.
        """
        async with self._lock:
            now = time.monotonic()
            cutoff = now - self.window_seconds

            # Count active requests (within window)
            active = sum(1 for ts in self._timestamps if ts >= cutoff)

            return {
                "requests_in_window": active,
                "max_requests": self.max_requests,
                "window_seconds": self.window_seconds,
                "requests_per_minute_limit": self.config.requests_per_minute,
                "capacity_used_percent": round(active / self.max_requests * 100, 1)
                if self.max_requests > 0
                else 0,
            }

    def reset(self) -> None:
        """Reset the rate limiter (clear all tracked requests)."""
        self._timestamps.clear()


# Global rate limiter instance
_rate_limiter: RateLimiter | None = None


def get_rate_limiter() -> RateLimiter:
    """Get the global rate limiter instance."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter


def configure_rate_limiter(requests_per_minute: int = 300) -> RateLimiter:
    """Configure and return the global rate limiter.

    Args:
        requests_per_minute: Max requests per minute (default: 300)

    Returns:
        The configured RateLimiter instance.
    """
    global _rate_limiter
    _rate_limiter = RateLimiter(
        config=RateLimitConfig(requests_per_minute=requests_per_minute)
    )
    return _rate_limiter
