"""
FastAPI app factory — lifespan, middleware, routes, health check.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.api.middleware import add_middleware
from src.api.routes import audit, photos, qc, vision
from src.core.config import get_settings
from src.core.logging import configure_logging, get_logger

settings = get_settings()
logger = get_logger("app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """App lifespan — startup and shutdown events."""
    configure_logging()
    logger.info("startup", app=settings.app_name, version=settings.app_version)
    # Auto-create tables if they don't exist
    from src.core.database import engine
    from src.models.models import Base, QCPacket, QCPhoto, QCFinding
    async with engine.begin() as conn:
        # Drop and recreate QC tables to pick up new columns
        from sqlalchemy import text
        await conn.execute(text("DROP TABLE IF EXISTS qc_findings CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS qc_photos CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS qc_packets CASCADE"))
        await conn.run_sync(Base.metadata.create_all)
    yield
    logger.info("shutdown")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="AI-powered auto damage estimate auditing",
        lifespan=lifespan,
    )

    # Middleware (order matters: RequestID → CORS → RateLimit → APIKey)
    add_middleware(app)

    # Routes
    app.include_router(audit.router)
    app.include_router(qc.router)
    app.include_router(photos.router)
    app.include_router(vision.router)

    @app.get("/health")
    async def health_check() -> dict:
        return {"status": "ok"}

    return app


# ASGI entrypoint
app = create_app()
