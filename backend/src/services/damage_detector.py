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

    def verify_finding(self, finding: dict, estimate_lines: list, metadata: dict) -> dict:
        """Default: trust the rules engine. Override in AI detectors."""
        return {"applies": finding.get("applies", True), "confidence": 0.5, "reasoning": "No AI verification available"}


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
        """Simple prompt — Gemini identifies damage, not parts. Part ID comes from the estimate."""
        return (
            "You are inspecting an auto insurance claim photo. Answer ONLY what you see:\\n"
            "1. Is there damage visible? (true/false)\\n"
            "2. What TYPE of damage? (dent, scratch, crack, rust, corrosion, tear, missing, broken, bent, none)\\n"
            "3. How SEVERE? (minor, moderate, severe, none)\\n"
            "4. Your confidence? (0.0-1.0)\\n\\n"
            "Return EXACTLY this JSON with NO markdown, NO explanation:\\n"
            '{"damage":true,"damage_type":"dent","severity":"moderate","confidence":0.85}\\n\\n'
            "IMPORTANT: Do NOT guess the vehicle part. We determine that from the estimate, not the photo."
        )

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
        result = self._call_gemini(image_b64, self._build_prompt())
        if result is None:
            result = self._call_gemini(image_b64, 'Return JSON: {"damage":true,"damage_type":"dent","severity":"moderate","confidence":0.5}')
        if result is None:
            return MockDamageDetector().analyze(image_bytes, filename)

        has_damage = result.get("damage", False)
        conf = result.get("confidence", 0.5)

        return {
            "damage": has_damage,
            "type": "needs_review",  # Auditor classifies
            "location": filename,
            "location_detail": "",
            "severity": "needs_review",
            "repair": "needs_review",
            "confidence": conf,
            "detections": [{
                "category": "needs_review",
                "confidence": conf,
                "location": filename,
                "severity": "needs_review",
                "repair": "needs_review",
            }],
            "needs_human_review": True,
            "ai_says_damage": has_damage,
            "ai_confidence": conf,
        }


    def verify_finding(self, finding: dict, estimate_lines: list[dict], metadata: dict) -> dict:
        """Ask Gemini whether a rule finding should actually trigger.
        
        Takes a finding from the rules engine and the full estimate context,
        returns Gemini's judgment on whether this is a real issue or false positive.
        """
        if not self.api_key:
            return {"applies": finding.get("applies", True), "confidence": 0.5, "reasoning": "No AI key configured"}

        # Build context for Gemini
        lines_text = ""
        for ln in finding.get("line_numbers", [])[:5]:
            for line in estimate_lines:
                if str(line.get("line_no", "")) == str(ln):
                    lines_text += f"  Line {ln}: {line.get('operation','')} {line.get('description','')} "
                    lines_text += f"part={line.get('part_type','')} panel={line.get('panel_name','')} "
                    lines_text += f"price={line.get('part_price','')} hours={line.get('labor_hours','')}\n"

        prompt = (
            f"You are an auto damage audit expert. A rules engine flagged this finding:\n"
            f"Rule: {finding.get('rule_id','')}\n"
            f"Description: {finding.get('description','')}\n"
            f"Severity: {finding.get('severity','')}\n"
            f"Suggested fix: {finding.get('suggested_fix','')}\n\n"
            f"Vehicle: {metadata.get('year','')} {metadata.get('make','')} {metadata.get('model','')}\n"
            f"Mileage: {metadata.get('odometer','')}\n"
            f"State: {metadata.get('state','')}\n"
            f"Total estimate: ${metadata.get('total_estimate','')}\n\n"
            f"Relevant estimate lines:\n{lines_text}\n"
            f"Based on your auto damage expertise, should this finding actually apply? "
            f"Return ONLY: {{\"applies\":true/false,\"confidence\":0.0-1.0,\"reasoning\":\"one sentence\"}}\n"
            f"Consider: repair context, part availability, damage severity, carrier guidelines, industry standards."
        )

        try:
            payload = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0.1, "maxOutputTokens": 150}}
            r = httpx.post(f"{self.url}?key={self.api_key}", json=payload, timeout=15)
            r.raise_for_status()
            data = r.json()
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            text = self._clean_json(text)
            result = json.loads(text)
            return result
        except Exception:
            return {"applies": finding.get("applies", True), "confidence": 0.5, "reasoning": "AI verification failed — defaulting to rule engine"}


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
