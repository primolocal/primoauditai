"""Quick integration test — verifies vision rule fires when photos exist."""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from rules_engine import RulesEngine
from rules.vision_rules import PhotoVerificationRule


def make_line(line_no, desc, op_label, part_type, row_type="operation"):
    return {
        "line_no": str(line_no),
        "description": desc,
        "operation_label": op_label,
        "operation_type": op_label,
        "operation_code": "RPL",
        "part_type": part_type,
        "part_number": "ABC-123",
        "row_type": row_type,
        "is_header": False,
        "is_included_labor": False,
        "is_sublet": False,
        "is_scan_related": False,
        "is_calibration_related": False,
        "supplement": "",
        "financial_signature": {
            "part_price": 450.0,
            "misc_amount": 0.0,
            "labor_amount_total": 195.0,
            "labor_hours_total": 3.0,
        },
    }


def test_vision_rule_fires_with_photos():
    """If photos exist, PhotoVerificationRule should fire."""
    photo = {
        "id": "asset_001",
        "url": "http://localhost:8000/assets/photo.jpg",
        "thumbnail_url": "http://localhost:8000/assets/thumbs/photo_thumb.jpg",
        "type": "exterior",
        "damage_area": "front_bumper",
        "clarity": "high",
        "confidence": 0.92,
    }

    data = {
        "claim": {
            "panels": [{
                "name": "Front End",
                "rows": [make_line("1", "Front Bumper Cover", "Replace", "OEM")]
            }],
            "validation": {}
        },
        "claim_meta": {"claim_number": "TEST-VISION", "carrier": "Test"},
        "evidence_matrix": {
            "processing_status": "complete",
            "documents": [],
            "photos": [photo],
        }
    }

    engine = RulesEngine()
    result = engine.evaluate_estimate(data)
    all_findings = (
        result["audit"]["base_findings"] +
        result["audit"]["carrier_overlays"]["natgen"]["findings"]
    )

    photo_verify_findings = [f for f in all_findings if "PHOTO_VERIFY" in f.get("rule_id", "")]
    print(f"Total findings: {len(all_findings)}")
    print(f"Photo verify findings: {len(photo_verify_findings)}")

    assert len(photo_verify_findings) >= 1, \
        f"Expected PhotoVerificationRule to fire, got findings: {[f['rule_id'] for f in all_findings]}"

    finding = photo_verify_findings[0]
    assert finding["rule_id"] == "PHOTO_VERIFY_001"
    assert len(finding.get("evidence_refs", [])) >= 1, "Should have evidence refs pointing to photos"
    assert any(e["type"] == "photo" for e in finding["evidence_refs"]), \
        "Evidence refs should include photo refs"

    print("✓ PhotoVerificationRule fires when photos exist")
    print(f"  Evidence refs: {len(finding['evidence_refs'])}")
    print(f"  Affected lines: {finding['affected_lines']}")


def test_vision_rule_skips_when_no_photos():
    """If no photos, PhotoVerificationRule should not fire."""
    data = {
        "claim": {
            "panels": [{
                "name": "Front End",
                "rows": [make_line("1", "Front Bumper Cover", "Replace", "OEM")]
            }],
            "validation": {}
        },
        "claim_meta": {"claim_number": "TEST-NO-PHOTOS", "carrier": "Test"},
        "evidence_matrix": {
            "processing_status": "not started",
            "documents": [],
            "photos": [],
        }
    }

    engine = RulesEngine()
    result = engine.evaluate_estimate(data)
    all_findings = (
        result["audit"]["base_findings"] +
        result["audit"]["carrier_overlays"]["natgen"]["findings"]
    )

    photo_verify_findings = [f for f in all_findings if "PHOTO_VERIFY" in f.get("rule_id", "")]
    assert len(photo_verify_findings) == 0, \
        "PhotoVerificationRule should not fire when no photos exist"
    print("✓ PhotoVerificationRule correctly skips when no photos")


if __name__ == "__main__":
    test_vision_rule_fires_with_photos()
    test_vision_rule_skips_when_no_photos()
    print("\n✓ Vision rules: all tests passed")
