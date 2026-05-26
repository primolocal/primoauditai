"""
HTML page-serving routes.
"""
import os

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

pages_router = APIRouter(tags=["pages"])


@pages_router.get("/audit")
async def full_audit_page():
    """Serve the full audit wizard UI."""
    try:
        with open(os.path.join(os.path.dirname(__file__), "..", "full_audit.html")) as f:
            html = f.read()
        return HTMLResponse(content=html)
    except Exception as e:
        return {"error": str(e)}


@pages_router.get("/toolbox")
async def toolbox_page():
    """Serve the Auditor Toolbox."""
    try:
        with open(os.path.join(os.path.dirname(__file__), "..", "toolbox.html")) as f:
            html = f.read()
        return HTMLResponse(content=html)
    except Exception as e:
        return {"error": str(e)}


@pages_router.get("/dashboard")
async def dashboard_page():
    """Serve the IANet audit dashboard."""
    try:
        with open(os.path.join(os.path.dirname(__file__), "..", "dashboard.html")) as f:
            html = f.read()
        return HTMLResponse(content=html)
    except Exception as e:
        return {"error": str(e)}


@pages_router.get("/workbench")
async def workbench_page():
    """Serve the auditor workbench."""
    try:
        with open(os.path.join(os.path.dirname(__file__), "..", "workbench.html")) as f:
            html = f.read()
        return HTMLResponse(content=html)
    except Exception as e:
        return {"error": str(e)}


@pages_router.get("/photos")
async def photo_tagger_page():
    """Serve the photo tagging tool."""
    try:
        with open(os.path.join(os.path.dirname(__file__), "..", "photo_tagger.html")) as f:
            html = f.read()
        return HTMLResponse(content=html)
    except Exception as e:
        return {"error": str(e)}


@pages_router.get("/qc")
async def qc_report_page():
    """Serve the QC report UI."""
    try:
        qc_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "frontend", "public", "qc.html")
        if not os.path.exists(qc_path):
            qc_path = os.path.join(os.path.dirname(__file__), "..", "qc.html")
        if not os.path.exists(qc_path):
            qc_path = os.path.join(os.path.dirname(__file__), "..", "qc.html")
        with open(qc_path) as f:
            html = f.read()
        return HTMLResponse(content=html)
    except Exception as e:
        return {"error": str(e)}
