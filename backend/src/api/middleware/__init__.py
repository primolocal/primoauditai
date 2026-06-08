"""
API middleware: request ID, CORS, rate limiting, API key auth.
"""
import time
import uuid
from collections.abc import Callable

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from src.core.config import get_settings
from src.core.logging import get_logger

logger = get_logger("middleware")
settings = get_settings()


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Add a unique request ID to every request and response."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = str(uuid.uuid4())[:8]
        request.state.request_id = request_id
        start = time.time()

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id

        duration = time.time() - start
        logger.info(
            "request",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=round(duration * 1000, 2),
            request_id=request_id,
        )
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-memory rate limiter: 100 req/min per IP."""

    _requests: dict = {}
    _window = 60  # seconds
    _max = 100

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        client = request.client.host if request.client else "unknown"
        now = time.time()
        window_start = now - self._window

        # Clean old entries and count current window
        self._requests[client] = [t for t in self._requests.get(client, []) if t > window_start]
        self._requests[client].append(now)

        if len(self._requests[client]) > self._max:
            return Response(
                content='{"detail":"Rate limit exceeded"}',
                status_code=429,
                media_type="application/json",
            )

        return await call_next(request)


class APIKeyMiddleware(BaseHTTPMiddleware):
    """Verify X-API-Key header against configured keys."""

    # Paths that don't require API key
    exempt_paths = {"/health", "/openapi.json", "/docs", "/redoc", "/api/qc", "/api/extract-photos"}

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path
        # Skip API key check for OPTIONS (CORS preflight) and exempt paths
        if request.method == "OPTIONS" or any(path.startswith(p) for p in self.exempt_paths):
            return await call_next(request)

        api_key = request.headers.get("X-API-Key", "")
        if api_key not in settings.api_key_list:
            return Response(
                content='{"detail":"Invalid or missing API key"}',
                status_code=401,
                media_type="application/json",
            )

        return await call_next(request)


def add_middleware(app: FastAPI) -> None:
    """Register all middleware in correct order."""
    # Order: RequestID → CORS → RateLimit → APIKey
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(APIKeyMiddleware)
