"""
Damage photo analysis — multiple backends: Gemini, Ollama, Mock fallback.
Set GEMINI_API_KEY env var to use Google Gemini Flash (free tier).
Set OLLAMA_HOST env var to use Ollama (requires local GPU or tunnel).
If neither available, falls back to mock detection.
"""

import base64
import json
import os
import random
import re
import httpx
from typing import Any

DAMAGE_CATEGORIES = ["dent", "scratch", "crack", "rust", "corrosion"]
LOCATIONS = ["front bumper", "rear bumper", "left fender", "right fender", "hood", "trunk", "left door", "right door", "wheel", "windshield", "roof"]


class BaseDamageDetector:
    def analyze(self, image_bytes: bytes, filename: str = "photo.jpg") -> dict[str, Any]:
        raise NotImplementedError


class MockDamageDetector(BaseDamageDetector):
    """Fallback mock detector when no real vision model available."""

    def analyze(self, image_bytes: bytes, filename: str = "photo.jpg") -> dict[str, Any]:
        num = random.choices([1, 2, 3, 0], weights=[0.4, 0.3, 0.2, 0.1])[0]
        detections = []
        for _ in range(num):
            detections.append({
                "category": random.choice(DAMAGE_CATEGORIES),
                "confidence": round(random.uniform(0.4, 0.95), 2),
                "bbox": [0.1, 0.2, 0.3, 0.3],
                "location": random.choice(LOCATIONS),
            })
        has = num > 0
        return {
            "damage": has,
            "type": detections[0]["category"] if detections else "other",
            "location": detections[0]["location"] if detections else "unknown",
            "confidence": detections[0]["confidence"] if detections else 0.0,
            "detections": detections,
        }


class GeminiVisionDetector(BaseDamageDetector):
    """Google Gemini Flash vision detection. Free tier available at aistudio.google.com/app/apikey"""

    def __init__(self, model: str = "gemini-1.5-flash-latest"):
        self.model = model
        self.api_key = os.getenv("GEMINI_API_KEY", "")
        self.url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

    def analyze(self, image_bytes: bytes, filename: str = "photo.jpg") -> dict[str, Any]:
        if not self.api_key:
            return MockDamageDetector().analyze(image_bytes, filename)

        image_b64 = base64.b64encode(image_bytes).decode()
        prompt = (
            "Analyze this auto insurance photo. Return ONLY valid JSON (no markdown, no explanation):\n"
            "{\n"
            '  "part": "specific vehicle component visible (hood, fender, door, bumper, windshield, wheel, dashboard, VIN plate, odometer, license plate, etc.)",\n'
            '  "damage": true/false,\n'
            '  "damage_type": "dent|scratch|crack|rust|corrosion|tear|missing|broken|bent|none",\n'
            '  "location_on_vehicle": "left front, right rear, center, etc.",\n'
            '  "severity": "minor|moderate|severe|none",\n'
            '  "repair_suggestion": "replace|repair|pdr|no action",\n'
            '  "confidence": 0.0-1.0\n'
            "}\n"
            "Look carefully at the image. Identify the EXACT vehicle part shown. "
            "Check for ANY damage, rust, corrosion, scratches, dents, cracks, missing parts, or discoloration."
        )
        payload = {
            "contents": [{
                "parts": [
                    {"text": prompt},
                    {"inline_data": {"mime_type": "image/jpeg", "data": image_b64}}
                ]
            }],
            "generationConfig": {"temperature": 0.2}
        }

        try:
            r = httpx.post(f"{self.url}?key={self.api_key}", json=payload, timeout=30)
            r.raise_for_status()
            data = r.json()
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            # Strip markdown code fences if present
            text = text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1] if "\n" in text else text[3:]
                if text.endswith("```"):
                    text = text[:-3]
            result = json.loads(text)
            return {
                "damage": result.get("damage", True),
                "type": result.get("damage_type", result.get("type", "other")),
                "location": result.get("part", result.get("location", filename)),
                "location_detail": result.get("location_on_vehicle", ""),
                "severity": result.get("severity", "moderate"),
                "repair": result.get("repair_suggestion", "repair"),
                "confidence": result.get("confidence", 0.5),
                "detections": [{
                    "category": result.get("damage_type", result.get("type", "other")),
                    "confidence": result.get("confidence", 0.5),
                    "location": result.get("part", result.get("location", filename)),
                    "severity": result.get("severity", "moderate"),
                    "repair": result.get("repair_suggestion", "repair"),
                }],
            }
        except Exception:
            return MockDamageDetector().analyze(image_bytes, filename)


class OllamaVisionDetector(BaseDamageDetector):
    """Ollama-based vision detection. Set OLLAMA_HOST env var if not localhost."""

    def __init__(self, model: str | None = None):
        self.model = model or os.getenv("VISION_MODEL", "llama3.2-vision:11b")
        self.ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self._available = None

    def _check(self) -> bool:
        if self._available is not None:
            return self._available
        try:
            r = httpx.get(f"{self.ollama_host}/api/tags", timeout=3)
            self._available = r.status_code == 200
        except Exception:
            self._available = False
        return self._available

    def analyze(self, image_bytes: bytes, filename: str = "photo.jpg") -> dict[str, Any]:
        if not self._check():
            return MockDamageDetector().analyze(image_bytes, filename)

        image_b64 = base64.b64encode(image_bytes).decode()
        payload = {
            "model": self.model,
            "messages": [{
                "role": "user",
                "content": "What type and where is the car damage? Return ONLY JSON: {\"damage\": true/false, \"type\": \"scratch|dent|crack|rust|none|other\", \"location\": \"panel\"}",
                "images": [image_b64],
            }],
            "stream": False,
        }

        try:
            r = httpx.post(f"{self.ollama_host}/api/chat", json=payload, timeout=60)
            r.raise_for_status()
            data = r.json()
            text = data["message"]["content"]
            m = re.search(r'\{[^}]*"damage"[^}]*\}', text, re.DOTALL)
            if m:
                result = json.loads(m.group(0))
                return {
                    "damage": result.get("damage", True),
                    "type": result.get("type", "other"),
                    "location": result.get("location", filename),
                    "confidence": 0.7,
                    "detections": [{"category": result.get("type", "other"), "confidence": 0.7, "location": result.get("location", filename)}],
                }
        except Exception:
            pass
        return MockDamageDetector().analyze(image_bytes, filename)


# Auto-select detector (priority: Gemini > Ollama > Mock)
if os.getenv("GEMINI_API_KEY"):
    detector = GeminiVisionDetector()
elif os.getenv("OLLAMA_HOST") or os.path.exists("/usr/local/bin/ollama"):
    detector = OllamaVisionDetector()
else:
    detector = MockDamageDetector()
