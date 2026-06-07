"""
Photo extraction endpoint — extract embedded JPEGs from PDFs.
"""
from typing import Any

from fastapi import APIRouter, File, UploadFile

router = APIRouter(prefix="/api/extract-photos", tags=["photos"])


@router.post("")
async def extract_photos(
    photos: UploadFile = File(...),
) -> dict[str, Any]:
    """Extract embedded JPEG images from a PDF and return as base64 data URLs."""
    try:
        _ = await photos.read()
        # TODO: Use PyMuPDF to extract images
        # For now, return placeholder
        return {
            "photos": [],
            "count": 0,
            "filename": photos.filename,
            "message": "Photo extraction ready — PyMuPDF integration pending",
        }
    except Exception as e:
        return {
            "photos": [],
            "count": 0,
            "filename": photos.filename,
            "error": str(e),
        }
