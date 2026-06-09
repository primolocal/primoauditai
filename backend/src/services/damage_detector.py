"""
CarDD damage detection prototype — mock implementation for testing the full pipeline.
Replace with real CarDDDetector or Ollama call in production.
"""

import random
from typing import Any

DAMAGE_CATEGORIES = ["dent", "scratch", "crack", "broken/missing", "corrosion/rust", "no damage"]
PANEL_LOCATIONS = [
    "front bumper", "rear bumper", "hood", "trunk",
    "right front door", "left front door", "right rear door", "left rear door",
    "right fender", "left fender", "right quarter panel", "left quarter panel",
    "roof", "grille", "headlamp", "taillamp"
]


class MockDamageDetector:
    """Simulates CarDD output for prototyping. Returns realistic damage detections."""
    
    def analyze(self, filename: str = "unknown.jpg") -> dict[str, Any]:
        """Return mock analysis matching the CarDD output format."""
        num_damages = random.choices([1, 2, 3, 0], weights=[0.4, 0.3, 0.2, 0.1])[0]
        detections = []
        
        for _ in range(num_damages):
            category = random.choice(DAMAGE_CATEGORIES[:5])  # exclude "no damage"
            detections.append({
                "category": category,
                "confidence": round(random.uniform(0.7, 0.98), 3),
                "bbox": [
                    random.randint(50, 300),
                    random.randint(50, 300),
                    random.randint(50, 200),
                    random.randint(50, 200),
                ],
                "severity": random.choice(["minor", "moderate", "severe"]),
                "location": random.choice(PANEL_LOCATIONS),
            })
        
        if not detections:
            detections.append({
                "category": "no damage",
                "confidence": 0.95,
                "bbox": [],
                "severity": "none",
                "location": "n/a",
            })
        
        return {
            "filename": filename,
            "detections": detections,
            "model": "mock-cardd-v0",
            "total_damages": len([d for d in detections if d["category"] != "no damage"]),
        }


# Singleton
detector = MockDamageDetector()


import base64
import json
import os
import re

import httpx


class OllamaVisionDetector:
    """Real damage detector using Ollama vision model (qwen3-vl:235b or gemma4:e4b)."""
    
    def __init__(self, model: str = None):
        self.ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
        self.model = model or os.getenv("VISION_MODEL", "qwen3-vl:235b")
    
    def analyze(self, image_path: str = None, image_bytes: bytes = None, filename: str = "unknown.jpg") -> dict:
        """Analyze a damage photo using Ollama vision model."""
        if image_bytes:
            image_b64 = base64.b64encode(image_bytes).decode()
        elif image_path:
            with open(image_path, "rb") as f:
                image_b64 = base64.b64encode(f.read()).decode()
        else:
            return {"error": "No image provided", "detections": []}

        prompt = """Analyze this car damage photo. Identify ALL damage types present:
- dent
- scratch
- crack
- broken/missing
- corrosion/rust
- no damage (if none visible)

Return ONLY valid JSON with this exact format:
{"detections": [{"category": "dent", "confidence": 0.92, "severity": "moderate", "location": "right front door"}]}"""

        try:
            import httpx
            import asyncio
            
            async def _call():
                async with httpx.AsyncClient(timeout=60.0) as client:
                    resp = await client.post(
                        f"{self.ollama_url}/api/chat",
                        json={
                            "model": self.model,
                            "messages": [{"role": "user", "content": prompt, "images": [image_b64]}],
                            "stream": False,
                        },
                    )
                    return resp.json()
            
            result = asyncio.run(_call())
            response_text = result.get("message", {}).get("content", "")
            
            # Parse JSON from response
            try:
                analysis = json.loads(response_text)
            except json.JSONDecodeError:
                match = re.search(r'\{[^{}]*"detections"[^{}]*\[.*?\][^{}]*\}', response_text, re.DOTALL)
                if match:
                    analysis = json.loads(match.group(0))
                else:
                    analysis = {"detections": [], "error": "Could not parse response"}
            
            return {
                "filename": filename,
                "detections": analysis.get("detections", []),
                "model": self.model,
                "total_damages": len([d for d in analysis.get("detections", []) if d.get("category") != "no damage"]),
            }
            
        except Exception as e:
            return {
                "filename": filename,
                "detections": [],
                "model": self.model,
                "error": str(e),
                "total_damages": 0,
            }


# Try to use real detector, fall back to mock
try:
    detector = OllamaVisionDetector()
    # Quick connectivity test
    import httpx
    resp = httpx.get(f"{detector.ollama_url}/api/tags", timeout=5)
    if resp.status_code == 200:
        print(f"Using real vision model: {detector.model}")
    else:
        raise Exception("Ollama not reachable")
except Exception:
    from src.services.damage_detector import MockDamageDetector
    detector = MockDamageDetector()
    print("Falling back to mock detector — Ollama unavailable")
