"""
Vision-based car damage detection endpoint.
Uses Ollama qwen3-vl:235b to classify damage in photos.
Can be upgraded to a trained CarDD model for production.
"""

import base64
import json
import os
from typing import Any

import httpx
from fastapi import APIRouter, File, HTTPException, Request, UploadFile

router = APIRouter(prefix="/api/vision", tags=["vision"])

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
VISION_MODEL = os.getenv("VISION_MODEL", "qwen3-vl:235b")

DAMAGE_CATEGORIES = ["dent", "scratch", "crack", "broken/missing", "corrosion/rust", "no damage"]


@router.post("/analyze")
async def analyze_damage_photo(
    request: Request,
    photo: UploadFile = File(...),
) -> dict[str, Any]:
    """Analyze a car damage photo using vision model.
    Returns damage categories with confidence scores.
    """
    if not photo.content_type or not photo.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Must be an image file")

    image_bytes = await photo.read()
    if len(image_bytes) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Image too large (max 10MB)")

    image_b64 = base64.b64encode(image_bytes).decode()

    prompt = f"""Analyze this car damage photo. Identify ALL damage types present from this list:
- dent
- scratch
- crack
- broken/missing
- corrosion/rust
- no damage

Return ONLY a JSON object with this format:
{{"damage_types": ["type1", "type2"], "severity": "minor|moderate|severe", "location": "brief description of where on the car", "confidence": 0.0-1.0}}"""

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{OLLAMA_URL}/api/chat",
                json={
                    "model": VISION_MODEL,
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt,
                            "images": [image_b64],
                        }
                    ],
                    "stream": False,
                },
            )
            resp.raise_for_status()
            result = resp.json()
            response_text = result.get("message", {}).get("content", "")

            # Try to parse JSON from response
            try:
                analysis = json.loads(response_text)
            except json.JSONDecodeError:
                # Extract JSON from markdown code block
                import re
                match = re.search(r"\{[^}]+\}", response_text)
                if match:
                    analysis = json.loads(match.group(0))
                else:
                    analysis = {
                        "damage_types": [],
                        "severity": "unknown",
                        "location": "unknown",
                        "confidence": 0.0,
                        "raw_response": response_text[:500],
                    }

            return {
                "filename": photo.filename,
                "analysis": analysis,
                "model": VISION_MODEL,
            }

    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail=f"Cannot connect to Ollama at {OLLAMA_URL}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Vision analysis failed: {str(e)}")


@router.post("/analyze-batch")
async def analyze_batch(
    request: Request,
    photos: list[UploadFile] = File(...),
) -> dict[str, Any]:
    """Analyze multiple damage photos in batch."""
    results = []
    for photo in photos:
        if photo.content_type and photo.content_type.startswith("image/"):
            image_bytes = await photo.read()
            image_b64 = base64.b64encode(image_bytes).decode()

            prompt = f"""Analyze this car damage photo. Identify damage types from: dent, scratch, crack, broken/missing, corrosion/rust, no damage.
Return JSON: {{"damage_types": ["type"], "severity": "minor|moderate|severe", "location": "brief"}}"""

            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    resp = await client.post(
                        f"{OLLAMA_URL}/api/chat",
                        json={
                            "model": VISION_MODEL,
                            "messages": [
                                {"role": "user", "content": prompt, "images": [image_b64]}
                            ],
                            "stream": False,
                        },
                    )
                    resp.raise_for_status()
                    result = resp.json()
                    response_text = result.get("message", {}).get("content", "")

                    try:
                        analysis = json.loads(response_text)
                    except json.JSONDecodeError:
                        import re
                        match = re.search(r"\{[^}]+\}", response_text)
                        analysis = json.loads(match.group(0)) if match else {"damage_types": [], "severity": "unknown"}

                    results.append({"filename": photo.filename, "analysis": analysis})
            except Exception as e:
                results.append({"filename": photo.filename, "error": str(e)})

    return {"results": results, "model": VISION_MODEL, "total": len(results)}


@router.get("/status")
async def vision_status(request: Request) -> dict[str, Any]:
    """Diagnostic: show which vision detector is active."""
    return get_detector_info()


@router.get("/demo")
async def demo_audit_vision(request: Request) -> dict[str, Any]:
    """Demonstrate the damage photo → audit cross-reference pipeline.
    Uses mock damage detection. Replace with real model in production."""
    from src.services.audit_vision import analyze_damage_photos

    demo_photos = [
        {"filename": "photo_001.jpg", "page": 1},
        {"filename": "photo_002.jpg", "page": 2},
        {"filename": "photo_003.jpg", "page": 3},
    ]

    demo_lines = [
        {"line_no": "5", "operation": "Repl", "panel_name": "HOOD", "description": "Replace hood"},
        {"line_no": "7", "operation": "Repl", "panel_name": "FRONT BUMPER", "description": "Replace front bumper cover"},
        {"line_no": "12", "operation": "Repl", "panel_name": "RT FENDER", "description": "Replace right fender"},
        {"line_no": "15", "operation": "Rpr", "panel_name": "RT FRONT DOOR", "description": "Repair right front door"},
    ]

    try:
        result = analyze_damage_photos(demo_photos, demo_lines)
        return {
            "demo": True,
            "model": result.get("model", "mock"),
            "findings_count": len(result.get("findings", [])),
            "photos_analyzed": len(demo_photos),
            **result,
        }
    except Exception as e:
        return {
            "demo": True,
            "model": "mock-fallback",
            "error": str(e),
            "findings_count": 0,
            "photos_analyzed": len(demo_photos),
        }


@router.post("/audit-photos")
async def audit_photos_from_pdf(
    request: Request,
    image_pdf: UploadFile = File(...),
    estimate_pdf: UploadFile = File(...),
) -> dict[str, Any]:
    """Extract photos from image PDF, cross-reference with estimate lines."""
    from src.photo_extractor import extract_photos_from_pdf
    from src.parser.pdf_estimate_parser import PDFEstimateParser
    from src.services.audit_vision import analyze_damage_photos

    # Validate
    if not image_pdf.filename or not image_pdf.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="image_pdf must be PDF")
    if not estimate_pdf.filename or not estimate_pdf.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="estimate_pdf must be PDF")

    # Read files
    img_bytes = await image_pdf.read()
    est_bytes = await estimate_pdf.read()

    # Extract photos
    try:
        raw_photos = extract_photos_from_pdf(img_bytes)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Failed to extract photos: {e}")

    # Parse estimate
    try:
        parser = PDFEstimateParser()
        parsed = parser.parse(est_bytes)
        estimate_lines = parsed.lines
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Failed to parse estimate: {e}")

    # Build photo list for analysis
    import base64
    photos_for_analysis = []
    for i, p in enumerate(raw_photos):
        b64 = base64.b64encode(p["bytes"]).decode() if p.get("bytes") else ""
        photos_for_analysis.append({
            "filename": f"photo_{p.get('page_num', 0)}_{p.get('image_index', i+1)}.{p.get('format', 'jpg')}",
            "data_url": f"data:image/{p.get('format', 'jpeg')};base64,{b64}",
            "page_num": p.get("page_num", 0),
            "width": p.get("width", 0),
            "height": p.get("height", 0),
        })

    # Run damage detection + cross-reference
    try:
        result = analyze_damage_photos(photos_for_analysis, estimate_lines)
    except Exception as e:
        return {
            "photos": [],
            "findings": [],
            "model": "mock-fallback",
            "error": str(e),
            "estimate_lines_checked": len(estimate_lines),
            "photos_extracted": len(raw_photos),
        }

    return {
        "photos_extracted": len(raw_photos),
        "photos_analyzed": len(photos_for_analysis),
        "estimate_lines": len(estimate_lines),
        "model": "mock-cardd-v0",
        "upgrade": "ollama pull llama3.2-vision:11b",
        **result,
    }
