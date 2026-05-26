"""
PrimoAuditAI Core API — main FastAPI application.
App creation, middleware, startup, and route mounting.
All endpoint logic lives in api/routes/.
"""
import os
import sys

# Ensure the backend directory is in the path to load local modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# --- Pydantic models (moved to schemas.py) ---
from schemas import (
    ActionPayload, FindingReviewPayload, AssetVerdictPayload,
    ActivityEventPayload, HermesAdvisoryPayload,
)

# --- Enterprise Security, Logging, Error Handling ---
from security import (
    RequestIDMiddleware,
    APIKeyMiddleware,
    RateLimitMiddleware,
)
from error_handlers import register_error_handlers
from logging_config import setup_logging, get_logger

# Initialize structured logging
LOG_FORMAT = os.environ.get("LOG_FORMAT", "text").lower()
setup_logging(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    json_format=(LOG_FORMAT == "json"),
)
logger = get_logger("primoaudit.api")

# --- App Creation ---
app = FastAPI(title="PrimoAuditAI Core API", version="1.0.0")

# --- Enterprise Middleware Stack ---
# 1. Request ID — injects X-Request-ID into every request/response
app.add_middleware(RequestIDMiddleware)

# 2. CORS — locked to specific origins via CORS_ALLOWED_ORIGINS env
origins = os.environ.get("CORS_ALLOWED_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in origins if o.strip()],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-API-Key", "X-Request-ID"],
)

# 3. Rate Limiting — sliding window, configurable RPM
app.add_middleware(RateLimitMiddleware, requests_per_minute=int(os.environ.get("RATE_LIMIT_RPM", "120")))

# 4. API Key Auth — requires X-API-Key on /api/ routes
app.add_middleware(APIKeyMiddleware)

# 5. Error Handlers — consistent error response format
register_error_handlers(app)

# 6. Register Ollama Cloud Hermes provider at startup
from services.ollama_cloud_hermes import patch_hermes_orchestrator
patch_hermes_orchestrator()


# --- Route Registration ---
# Learning API (no prefix, routes defined in router)
from api.learning_api import router as learning_router
app.include_router(learning_router)

# Full Audit API
from api.full_audit import full_audit_router
app.include_router(full_audit_router)

# Audit routes (upload, run, status, GET, findings, scores, narratives, etc.)
from api.routes.audit import audit_router
app.include_router(audit_router)

# Hermes routes (retry, mock advisory)
from api.routes.hermes import hermes_router
app.include_router(hermes_router)

# HTML page-serving routes
from api.routes.pages import pages_router
app.include_router(pages_router)


# --- Health Check ---
@app.get("/")
def health_check():
    return {"status": "ok", "service": "PrimoAuditAI"}


# --- Asset Serving ---
from fastapi.responses import StreamingResponse
from fastapi import HTTPException


@app.get("/assets/{storage_key:path}")
async def get_asset(storage_key: str):
    from storage_service import StorageService
    try:
        stream = StorageService.get_file_stream(storage_key)
        return StreamingResponse(stream)
    except Exception as e:
        raise HTTPException(status_code=404, detail="Asset not found")


@app.get("/assets/thumbs/{storage_key:path}")
async def get_asset_thumb(storage_key: str):
    from storage_service import StorageService
    try:
        stream = StorageService.get_file_stream(storage_key)
        return StreamingResponse(stream)
    except Exception as e:
        raise HTTPException(status_code=404, detail="Thumbnail not found")


# --- Startup ---
@app.on_event("startup")
def startup_event():
    # Create tables if they don't exist (for dev/SQLite; production uses Alembic)
    from database.database import Base, engine
    Base.metadata.create_all(bind=engine)
