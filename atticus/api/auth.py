"""Optional API token auth + simple in-process rate limiting."""

from __future__ import annotations

import os
import time
from collections import defaultdict, deque
from typing import Any, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from atticus.core.secrets import get_credential


class ApiAuthMiddleware(BaseHTTPMiddleware):
    """When ATTICUS_API_TOKEN is set, require X-Atticus-Api-Token on /v1/*."""

    PUBLIC_PREFIXES = (
        "/health",
        "/ready",
        "/ui",
        "/terminal",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/favicon.ico",
    )

    def __init__(self, app: Any, *, token_env: str, token_value: str | None = None) -> None:
        super().__init__(app)
        self._token_env = token_env
        self._token_value = token_value

    def _expected(self) -> str | None:
        if self._token_value is not None:
            return self._token_value or None
        if not self._token_env:
            return None
        return get_credential(self._token_env)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path
        if path == "/" or any(path == p or path.startswith(p + "/") or path.startswith(p) for p in self.PUBLIC_PREFIXES):
            # /ui and health stay open for local desk use; mutating /v1 is gated.
            if not path.startswith("/v1"):
                return await call_next(request)
        expected = self._expected()
        if not expected:
            return await call_next(request)
        if not path.startswith("/v1"):
            return await call_next(request)
        provided = request.headers.get("x-atticus-api-token")
        if not provided or provided != expected:
            return JSONResponse(
                status_code=401,
                content={
                    "error": {
                        "code": "unauthorized",
                        "message": "Missing or invalid X-Atticus-Api-Token.",
                    }
                },
            )
        return await call_next(request)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Fixed-window per-client rate limit for /v1 routes."""

    def __init__(self, app: Any, *, per_minute: int = 120) -> None:
        super().__init__(app)
        self._per_minute = max(0, per_minute)
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if self._per_minute <= 0 or not request.url.path.startswith("/v1"):
            return await call_next(request)
        client = request.client.host if request.client else "unknown"
        now = time.monotonic()
        window = self._hits[client]
        cutoff = now - 60.0
        while window and window[0] < cutoff:
            window.popleft()
        if len(window) >= self._per_minute:
            return JSONResponse(
                status_code=429,
                content={
                    "error": {
                        "code": "rate_limited",
                        "message": f"Rate limit exceeded ({self._per_minute}/min).",
                    }
                },
                headers={"Retry-After": "60"},
            )
        window.append(now)
        return await call_next(request)
