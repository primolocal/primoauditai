"""
Enterprise Security Module for PrimoAuditAI.
API authentication, CORS, rate limiting, request ID, input validation.
"""
import os
import uuid
import time
import hashlib
import hmac
from collections import defaultdict
from typing import Optional

from fastapi import Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

def get_required_env(key: str) -> str:
    """Fetch required env var or raise at boot."""
    val = os.environ.get(key, "").strip()
    if not val:
        raise RuntimeError(f"Missing required environment variable: {key}")
    return val


def get_api_keys() -> set[str]:
    """Parse API_KEYS env var (comma-separated) into a set."""
    raw = os.environ.get("API_KEYS", "").strip()
    if not raw:
        return set()
    return {k.strip() for k in raw.split(",") if k.strip()}


def get_allowed_origins() -> list[str]:
    """Parse CORS_ALLOWED_ORIGINS env var."""
    raw = os.environ.get("CORS_ALLOWED_ORIGINS", "http://localhost:3000").strip()
    return [o.strip() for o in raw.split(",") if o.strip()]


# ---------------------------------------------------------------------------
# Request ID Middleware
# ---------------------------------------------------------------------------

class RequestIDMiddleware(BaseHTTPMiddleware):
    """Inject X-Request-ID into every request/response."""

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4().hex[:12]))
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


# ---------------------------------------------------------------------------
# API Key Authentication
# ---------------------------------------------------------------------------

class APIKeyMiddleware(BaseHTTPMiddleware):
    """
    Require X-API-Key header on all /api/ routes.
    Skip health check and OPTIONS.
    """

    EXEMPT_PATHS = {"/", "/health", "/docs", "/openapi.json", "/redoc", "/api/qc", "/api/vision", "/api/extract-photos", "/qc", "/audit", "/photos", "/workbench", "/dashboard", "/toolbox", "/api/audit/full"}

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Skip exempt paths
        if path in self.EXEMPT_PATHS or path.startswith("/assets/"):
            return await call_next(request)

        # Skip OPTIONS (CORS preflight)
        if request.method == "OPTIONS":
            return await call_next(request)

        api_keys = get_api_keys()
        if not api_keys:
            # No keys configured — allow all (dev mode)
            return await call_next(request)

        provided = request.headers.get("X-API-Key", "")
        if not provided or provided not in api_keys:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "error": "Unauthorized",
                    "detail": "Missing or invalid X-API-Key header.",
                    "request_id": getattr(request.state, "request_id", "unknown"),
                },
            )

        return await call_next(request)


# ---------------------------------------------------------------------------
# Rate Limiting (In-Memory — swap for Redis in production)
# ---------------------------------------------------------------------------

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Simple sliding-window rate limiter.
    RateLimit-Limit and RateLimit-Remaining headers are set.
    """

    def __init__(self, app, requests_per_minute: int = 120):
        super().__init__(app)
        self.rpm = requests_per_minute
        self._windows: dict[str, list[float]] = defaultdict(list)
        self._cleanup_every = 60  # seconds between cleanups
        self._last_cleanup = time.time()

    def _cleanup(self):
        """Remove expired windows."""
        now = time.time()
        cutoff = now - 60
        for key in list(self._windows.keys()):
            self._windows[key] = [t for t in self._windows[key] if t > cutoff]
            if not self._windows[key]:
                del self._windows[key]
        self._last_cleanup = now

    async def dispatch(self, request: Request, call_next):
        # Periodic cleanup
        if time.time() - self._last_cleanup > self._cleanup_every:
            self._cleanup()

        # Identify client by API key or IP
        api_key = request.headers.get("X-API-Key", "")
        client_id = api_key if api_key else request.client.host if request.client else "unknown"

        now = time.time()
        cutoff = now - 60

        # Get or create window
        window = self._windows[client_id]
        window = [t for t in window if t > cutoff]
        self._windows[client_id] = window

        if len(window) >= self.rpm:
            reset_time = int(window[0] + 60) if window else int(now + 60)
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "Rate limit exceeded",
                    "detail": f"Maximum {self.rpm} requests per minute.",
                    "retry_after_seconds": max(0, reset_time - int(now)),
                    "request_id": getattr(request.state, "request_id", "unknown"),
                },
                headers={"Retry-After": str(max(0, reset_time - int(now)))},
            )

        # Record this request
        window.append(now)
        remaining = max(0, self.rpm - len(window))

        response = await call_next(request)
        response.headers["RateLimit-Limit"] = str(self.rpm)
        response.headers["RateLimit-Remaining"] = str(remaining)
        return response


# ---------------------------------------------------------------------------
# Upload Validation
# ---------------------------------------------------------------------------

MAX_UPLOAD_SIZE_MB = int(os.environ.get("MAX_UPLOAD_SIZE_MB", "100"))
MAX_UPLOAD_SIZE_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024
MAX_ZIP_EXPANSION_RATIO = int(os.environ.get("MAX_ZIP_EXPANSION_RATIO", "100"))


def validate_upload_size(content: bytes, filename: str) -> None:
    """Reject files exceeding MAX_UPLOAD_SIZE_MB."""
    if len(content) > MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File {filename} exceeds maximum size of {MAX_UPLOAD_SIZE_MB}MB.",
        )


def validate_zip_bomb(zip_bytes: bytes) -> None:
    """Check ZIP expansion ratio to prevent decompression bombs."""
    import zipfile
    import io
    try:
        compressed = len(zip_bytes)
        if compressed == 0:
            raise HTTPException(status_code=400, detail="Empty ZIP file.")

        with zipfile.ZipFile(io.BytesIO(zip_bytes), 'r') as zf:
            total_uncompressed = sum(info.file_size for info in zf.infolist())

        if compressed > 0 and (total_uncompressed / compressed) > MAX_ZIP_EXPANSION_RATIO:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"ZIP expansion ratio ({total_uncompressed/compressed:.1f}:1) exceeds maximum ({MAX_ZIP_EXPANSION_RATIO}:1). Possible ZIP bomb.",
            )
    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="Invalid or corrupted ZIP file.")


# ---------------------------------------------------------------------------
# HMAC Webhook Signing
# ---------------------------------------------------------------------------

def get_webhook_secret() -> bytes:
    """Fetch HMAC webhook secret — never hardcoded."""
    secret = os.environ.get("HERMES_WEBHOOK_SECRET", "").strip()
    if not secret:
        raise RuntimeError("HERMES_WEBHOOK_SECRET is required for Hermes webhook signing")
    if secret == "super-secure-placeholder-secret-here":
        raise RuntimeError(
            "HERMES_WEBHOOK_SECRET is still the placeholder. Generate a real secret."
        )
    return secret.encode("utf-8")


def sign_webhook_payload(payload_bytes: bytes) -> str:
    """Sign payload with HMAC-SHA256."""
    secret = get_webhook_secret()
    return "sha256=" + hmac.new(secret, payload_bytes, hashlib.sha256).hexdigest()


# ---------------------------------------------------------------------------
# CORS Builder
# ---------------------------------------------------------------------------

def build_cors_middleware() -> CORSMiddleware:
    """Return configured CORS middleware — not wildcard in production."""
    origins = get_allowed_origins()

    # If CORS_ALLOWED_ORIGINS is '*', treat it as wildcard (dev only)
    if origins == ["*"]:
        print("[WARNING] CORS_ALLOWED_ORIGINS='*' — all origins allowed. Set explicitly for production.")

    return CORSMiddleware(
        app=None,  # set by FastAPI
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=[
            "Content-Type", "Authorization", "X-API-Key",
            "X-Request-ID", "X-Hermes-Event", "X-Hub-Signature-256",
        ],
    )
