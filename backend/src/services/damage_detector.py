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
