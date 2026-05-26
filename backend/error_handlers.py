"""
Centralized exception handlers for FastAPI.
Consistent error response format with correlation IDs.
"""
import traceback
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import JSONResponse
from logging_config import get_logger

logger = get_logger(__name__)


def register_error_handlers(app: FastAPI) -> None:
    """Register all exception handlers on the FastAPI app."""

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        request_id = getattr(request.state, "request_id", "unknown")
        logger.warning(
            f"HTTP {exc.status_code} on {request.url.path} — {exc.detail}",
            extra={"request_id": request_id},
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": "Request Error",
                "detail": exc.detail,
                "request_id": request_id,
            },
        )

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError):
        request_id = getattr(request.state, "request_id", "unknown")
        logger.warning(
            f"Validation error on {request.url.path}: {exc}",
            extra={"request_id": request_id},
        )
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": "Validation Error",
                "detail": str(exc),
                "request_id": request_id,
            },
        )

    @app.exception_handler(RuntimeError)
    async def runtime_error_handler(request: Request, exc: RuntimeError):
        request_id = getattr(request.state, "request_id", "unknown")
        logger.error(
            f"Runtime error on {request.url.path}: {exc}",
            extra={"request_id": request_id},
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "Internal Error",
                "detail": "An internal error occurred. Check server logs.",
                "request_id": request_id,
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        request_id = getattr(request.state, "request_id", "unknown")
        logger.critical(
            f"Unhandled exception on {request.url.path}: {exc}\n{traceback.format_exc()}",
            extra={"request_id": request_id},
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "Internal Server Error",
                "detail": "An unexpected error occurred. Check server logs.",
                "request_id": request_id,
            },
        )
