"""In-process rate limiter for POST /auth/login.

ponytail: per-IP deque of timestamps. Only failed attempts (401/429) consume a
slot. Single-worker required (state is per-process). Promote to Redis when
horizontal scale matters.
"""
from __future__ import annotations

import time
from collections import defaultdict, deque

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

_WINDOW_SECONDS = 60
_MAX_ATTEMPTS = 5

_attempts: dict[str, deque[float]] = defaultdict(deque)


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _retry_after(bucket: deque[float], now: float) -> int:
    if not bucket:
        return 1
    return max(1, int(_WINDOW_SECONDS - (now - bucket[0])) + 1)


class LoginRateLimitMiddleware(BaseHTTPMiddleware):
    """Consume a slot only on failed POST /auth/login (401 or 429)."""

    async def dispatch(self, request: Request, call_next):
        if request.url.path != "/auth/login" or request.method != "POST":
            return await call_next(request)

        ip = _client_ip(request)
        now = time.monotonic()
        bucket = _attempts[ip]

        while bucket and now - bucket[0] > _WINDOW_SECONDS:
            bucket.popleft()

        if len(bucket) >= _MAX_ATTEMPTS:
            return JSONResponse(
                {"detail": "Too many login attempts"},
                status_code=429,
                headers={"Retry-After": str(_retry_after(bucket, now))},
            )

        response = await call_next(request)
        if response.status_code in (401, 429):
            bucket.append(now)
        return response