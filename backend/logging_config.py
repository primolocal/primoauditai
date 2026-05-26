"""
Structured logging with request correlation IDs.
Replaces all print() statements with proper log levels.
"""
import logging
import sys
from contextvars import ContextVar
from typing import Optional

# ---------------------------------------------------------------------------
# Correlation ID (thread-safe context variable)
# ---------------------------------------------------------------------------

_correlation_id: ContextVar[Optional[str]] = ContextVar("correlation_id", default=None)


def set_correlation_id(cid: str) -> None:
    _correlation_id.set(cid)


def get_correlation_id() -> str:
    return _correlation_id.get() or "unknown"


# ---------------------------------------------------------------------------
# Custom Formatter
# ---------------------------------------------------------------------------

class PrimoAuditFormatter(logging.Formatter):
    """Adds correlation_id to every log line."""

    def format(self, record: logging.LogRecord) -> str:
        record.correlation_id = get_correlation_id()
        return super().format(record)


# ---------------------------------------------------------------------------
# Logger Factory
# ---------------------------------------------------------------------------

def get_logger(name: str) -> logging.Logger:
    """Get a configured logger instance."""
    return logging.getLogger(name)


# ---------------------------------------------------------------------------
# Initialize
# ---------------------------------------------------------------------------

def setup_logging(level: str = "INFO", json_format: bool = False) -> None:
    """
    Configure root logger with structured output.
    Set LOG_FORMAT=json in env for JSON log lines (for log aggregators).
    """
    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Clear existing handlers
    root.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)

    if json_format:
        # JSON format for ELK / Datadog / CloudWatch
        import json as _json
        from datetime import datetime, timezone

        class JSONFormatter(logging.Formatter):
            def format(self, record):
                return _json.dumps({
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "level": record.levelname,
                    "logger": record.name,
                    "correlation_id": getattr(record, "correlation_id", "unknown"),
                    "message": record.getMessage(),
                    "module": record.module,
                    "line": record.lineno,
                }, default=str)

        handler.setFormatter(JSONFormatter())
    else:
        # Human-readable with correlation ID
        fmt = (
            "[%(asctime)s] [%(levelname)-7s] [%(correlation_id)s] "
            "%(name)s:%(lineno)d — %(message)s"
        )
        handler.setFormatter(PrimoAuditFormatter(fmt, datefmt="%Y-%m-%dT%H:%M:%S"))

    root.addHandler(handler)

    # Silence noisy libs
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("botocore").setLevel(logging.WARNING)
    logging.getLogger("PIL").setLevel(logging.WARNING)
