"""
Photo extraction endpoint — extract embedded JPEGs from PDFs.
"""
from typing import Any

from fastapi import APIRouter, File, UploadFile

from src.parser.pdf_estimate_parser import PDFPhotoExtractor

router = APIRouter(prefix="/api/extract-photos", tags=["photos"])


@router.post("")
async def extract_photos(
    photos: UploadFile = File(...),
) -> dict[str, Any]:
    """Extract embedded JPEG images from a PDF and return as base64 data URLs."""
    try:
        content = await photos.read()
        extractor = PDFPhotoExtractor()
        extracted = extractor.extract(content)
        return {
            "photos": extracted,
            "count": len(extracted),
            "filename": photos.filename,
        }
    except Exception as e:
        return {
            "photos": [],
            "count": 0,
            "filename": photos.filename,
            "error": str(e),
        }
