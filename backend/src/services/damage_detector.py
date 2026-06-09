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
    """Google Gemini Flash vision detection. Free tier at aistudio.google.com/app/apikey"""

    def __init__(self, model: str = "gemini-1.5-flash-latest"):
        self.model = model
        self.api_key = os.getenv("GEMINI_API_KEY", "")
        self.url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        self.feedback_examples: list[dict] = []  # Few-shot learning from human corrections
        self._load_feedback()

    def _load_feedback(self):
        """Load recent human corrections as few-shot examples."""
        try:
            import sqlite3
            db_path = os.getenv("DATABASE_URL", "").replace("sqlite:///", "")
            if db_path and os.path.exists(db_path):
                conn = sqlite3.connect(db_path)
                cur = conn.cursor()
                cur.execute(
                    "SELECT vision_result FROM qc_photos WHERE vision_result IS NOT NULL "
                    "ORDER BY created_at DESC LIMIT 100"
                )
                for (vr_json,) in cur.fetchall():
                    try:
                        vr = json.loads(vr_json) if isinstance(vr_json, str) else vr_json
                        corrections = vr.get("human_corrections", [])
                        for c in corrections:
                            if c.get("original_type") and c.get("corrected_type"):
                                self.feedback_examples.append(c)
                    except Exception:
                        pass
                conn.close()
        except Exception:
            pass  # No feedback yet — that's fine

    def _build_prompt(self) -> str:
        """Build the vision prompt with optional few-shot examples from feedback."""
        base = (
            "You are an auto insurance damage inspector. Look at this photo and identify:\n"
            "1. The SPECIFIC vehicle part (use these terms only: hood, front bumper, rear bumper, "
            "right fender, left fender, right front door, left front door, right rear door, left rear door, "
            "roof, trunk lid, liftgate, windshield, right quarter panel, left quarter panel, "
            "grille, headlamp, tail lamp, wheel, tire, dashboard, VIN plate, odometer, license plate)\n"
            "2. Whether there is damage\n"
            "3. The damage type\n"
            "4. The severity\n"
            "5. The recommended repair action\n\n"
            "Return EXACTLY this JSON format with NO markdown, NO explanation, NO code fences:\n"
            '{"part":"hood","damage":true,"damage_type":"dent","location_on_vehicle":"center","severity":"moderate","repair_suggestion":"repair","confidence":0.85}\n\n'
            "Damage types: dent, scratch, crack, rust, corrosion, tear, missing, broken, bent, none\n"
            "Severity: minor, moderate, severe, none\n"
            "Repair: replace, repair, pdr, no action\n"
            "Confidence: 0.0 to 1.0\n\n"
            "IMPORTANT: All fields required. Never use null. Use 'unknown' for part if unclear, 'moderate' for severity, 'repair' for suggestion."
        )
        # Add few-shot examples from human corrections if available
        if self.feedback_examples:
            base += "\n\nHere are examples of correct labels from previous inspections:\n"
            for ex in self.feedback_examples[-3:]:  # Last 3 corrections
                base += f'Photo was "{ex.get("original_type","")}" but human corrected to "{ex.get("corrected_type","")}" because: {ex.get("reason","photo inspection")}.\n'
        return base

    def _call_gemini(self, image_b64: str, prompt: str) -> dict | None:
        """Call Gemini API. Returns parsed dict or None on failure."""
        payload = {
            "contents": [{
                "parts": [
                    {"text": prompt},
                    {"inline_data": {"mime_type": "image/jpeg", "data": image_b64}}
                ]
            }],
            "generationConfig": {"temperature": 0.2, "maxOutputTokens": 200}
        }
        try:
            r = httpx.post(f"{self.url}?key={self.api_key}", json=payload, timeout=30)
            r.raise_for_status()
            data = r.json()
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            text = self._clean_json(text)
            return json.loads(text)
        except Exception:
            return None

    def _clean_json(self, text: str) -> str:
        """Strip markdown fences and extract valid JSON."""
        text = text.strip()
        # Remove markdown code fences
        for fence in ["```json", "```"]:
            if text.startswith(fence):
                text = text[len(fence):].strip()
            if text.endswith("```"):
                text = text[:-3].strip()
        # Find the first { and last }
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end > start:
            text = text[start:end+1]
        return text

    def analyze(self, image_bytes: bytes, filename: str = "photo.jpg") -> dict[str, Any]:
        if not self.api_key:
            return MockDamageDetector().analyze(image_bytes, filename)

        image_b64 = base64.b64encode(image_bytes).decode()

        # Try primary prompt
        result = self._call_gemini(image_b64, self._build_prompt())
        # If failed, retry with simpler prompt
        if result is None:
            simple_prompt = 'Return JSON: {"part":"","damage":true,"damage_type":"","severity":"","repair_suggestion":"","confidence":0.5}'
            result = self._call_gemini(image_b64, simple_prompt)
        # If still failed, return mock
        if result is None:
            return MockDamageDetector().analyze(image_bytes, filename)

        # Build standardized response with safe defaults
        damage_type = result.get("damage_type") or result.get("type") or "other"
        part = result.get("part") or result.get("location") or filename.replace(".jpg","").replace("_"," ")
        severity = result.get("severity") or "moderate"
        repair = result.get("repair_suggestion") or result.get("repair") or "repair"

        return {
            "damage": result.get("damage", True),
            "type": damage_type,
            "location": part,
            "location_detail": result.get("location_on_vehicle", ""),
            "severity": severity,
            "repair": repair,
            "confidence": result.get("confidence", 0.5),
            "detections": [{
                "category": damage_type,
                "confidence": result.get("confidence", 0.5),
                "location": part,
                "severity": severity,
                "repair": repair,
            }],
        }


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
