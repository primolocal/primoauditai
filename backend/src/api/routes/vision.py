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
