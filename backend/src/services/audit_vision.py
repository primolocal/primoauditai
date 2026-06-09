import base64
"""
Damage Photo Analysis — plugs into the audit workflow.
Prototype: uses MockDamageDetector (simulated CarDD output).
Production: swap to Ollama qwen3-vl or trained CarDD model.

To pull the vision model when Ollama Cloud session resets:
  ollama pull llama3.2-vision:11b    # ~8GB, good accuracy
  ollama pull minicpm-v:8b           # ~5GB, faster, decent
  ollama pull qwen3-vl:235b          # Cloud only, best accuracy
"""

from typing import Any

from src.services.damage_detector import detector as damage_detector


def analyze_damage_photos(
    photos: list[dict[str, Any]],  # [{filename, data_url, ...}]
    estimate_lines: list[dict[str, Any]],
) -> dict[str, Any]:
    """Analyze damage photos and cross-reference with estimate lines.
    
    Returns findings about mismatches between photos and estimate claims.
    """
    findings = []
    photo_analyses = []

    for photo in photos:
        filename = photo.get("filename", "unknown.jpg")
        # Extract bytes from data_url if present
        image_bytes = b""
        data_url = photo.get("data_url", "")
        if data_url.startswith("data:image"):
            b64_part = data_url.split(",", 1)[1] if "," in data_url else ""
            image_bytes = base64.b64decode(b64_part) if b64_part else b""
        result = damage_detector.analyze(image_bytes or b"", filename)
        photo_analyses.append(result)

    # Cross-reference: does the estimate claim operations the photos don't support?
    damage_panels = set()
    for analysis in photo_analyses:
        for det in analysis.get("detections", []):
            if det["category"] != "no damage":
                damage_panels.add(det.get("location", "").lower())

    for line in estimate_lines:
        op = line.get("operation", "")
        panel = (line.get("panel_name") or line.get("description") or "").lower()
        
        # Flag replace operations where no matching damage photo exists
        if op == "Repl" and panel:
            if not any(panel in dp or dp in panel for dp in damage_panels if dp):
                findings.append({
                    "rule_id": "VISION_001",
                    "severity": "medium",
                    "description": f"Replace operation on {panel} but no damage photo found for this panel",
                    "line_numbers": [int(line["line_no"])] if line.get("line_no", "").isdigit() else [],
                    "suggested_fix": "Verify damage photos cover all replaced panels",
                })

    # Flag photos showing damage on panels NOT in the estimate
    for analysis in photo_analyses:
        for det in analysis.get("detections", []):
            loc = det.get("location", "").lower()
            if det["category"] != "no damage" and loc:
                matched = any(
                    loc in (line.get("panel_name") or line.get("description") or "").lower()
                    or (line.get("panel_name") or line.get("description") or "").lower() in loc
                    for line in estimate_lines
                )
                if not matched:
                    findings.append({
                        "rule_id": "VISION_002",
                        "severity": "low",
                        "description": f"Damage photo shows {det['category']} on {loc} but no estimate line covers this panel",
                        "line_numbers": [],
                        "suggested_fix": "Verify if this damage should be included in estimate",
                    })

    return {
        "photo_analyses": photo_analyses,
        "cross_reference_findings": findings,
        "total_photos": len(photos),
        "damage_detected": len([d for a in photo_analyses for d in a.get("detections", []) if d["category"] != "no damage"]),
    }
