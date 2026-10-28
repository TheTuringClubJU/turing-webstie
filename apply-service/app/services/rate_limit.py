"""Per-process sliding-window rate limiting for application submissions."""

import threading
import time
from collections import deque

from fastapi import Request

from app.errors import ApiError


class SlidingWindowRateLimiter:
    """Track request timestamps independently for each client IP."""

    def __init__(self) -> None:
        self._requests: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def allow(self, client_ip: str, limit: int, window_seconds: int) -> bool:
        now = time.monotonic()
        cutoff = now - window_seconds
        with self._lock:
            expired_clients = []
            for ip, timestamps in self._requests.items():
                while timestamps and timestamps[0] <= cutoff:
                    timestamps.popleft()
                if not timestamps:
                    expired_clients.append(ip)
            for ip in expired_clients:
                del self._requests[ip]

            timestamps = self._requests.setdefault(client_ip, deque())
            if len(timestamps) >= limit:
                return False
            timestamps.append(now)
            return True


async def enforce_application_rate_limit(request: Request) -> None:
    """Enforce the configured limit using the direct ASGI peer address."""
    settings = request.app.state.settings
    if not settings.rate_limit_enabled:
        return

    client_ip = request.client.host if request.client else "unknown"
    limiter: SlidingWindowRateLimiter = request.app.state.rate_limiter
    if not limiter.allow(
        client_ip,
        settings.rate_limit_requests,
        settings.rate_limit_window_seconds,
    ):
        raise ApiError(
            429,
            "rate_limited",
            "Too many requests. Please try again later.",
        )
