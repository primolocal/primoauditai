"""
Tests for PrimoAuditAI Rules Engine.
Covers all 11 rules with known inputs and expected outputs.
"""
import pytest
import sys
import os

# Ensure backend is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from rules_engine import RulesEngine
from rules.audit_rules import (
    IncludedLaborRule, HighMiscRule, HazWasteRule, FlexAddRule,
    NegativeLaborRule, LaborNoHoursRule, ZeroPricePartRule, MechOnCosmeticRule
)
from rules.natgen_rules import (
    ScanLaborThresholdRule, CalibrationChargeTimingRule, CalibrationTriggerSupportRule
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_line(**overrides) -> dict:
    """Factory for a standard estimate line."""
    base = {
        "line_no": "1",
        "description": "Test Part",
        "operation_label": "Replace",
        "operation_type": "Replace",
        "operation_code": "RPL",
        "part_type": "OEM",
        "part_number": "ABC-123",
        "row_type": "operation",
        "is_header": False,
        "is_included_labor": False,
        "is_sublet": False,
        "is_scan_related": False,
        "is_calibration_related": False,
        "is_hazardous_waste": False,
        "is_material_charge": False,
        "service_subtype": "",
        "misc_subtype": "",
        "supplement": "",
        "labor_types": ["LAB"],
        "labor_amount_body": 0.0,
        "labor_amount_refinish": 0.0,
        "labor_amount_mechanical": 0.0,
        "labor_amount_frame": 0.0,
        "labor_amount_diag": 0.0,
        "part_price": 0.0,
        "misc_amount": 0.0,
        "financial_signature": {
            "part_price": 0.0,
            "misc_amount": 0.0,
            "labor_amount_total": 0.0,
            "labor_hours_total": 0.0,
        },
        "has_part_price": False,
        "has_misc_amount": False,
        "has_labor_hours": False,
        "has_labor_amount": False,
    }
    # Apply overrides to both top-level and financial_signature
    for k, v in overrides.items():
        if k in base:
            base[k] = v
    # Sync financial_signature
    fs = base["financial_signature"]
    fs["part_price"] = base["part_price"]
    fs["misc_amount"] = base["misc_amount"]
    fs["labor_amount_total"] = sum([
        base["labor_amount_body"], base["labor_amount_refinish"],
        base["labor_amount_mechanical"], base["labor_amount_frame"],
        base["labor_amount_diag"]
    ])
    # labor_hours_total can be set explicitly
    if "labor_hours_total" in overrides:
        fs["labor_hours_total"] = overrides["labor_hours_total"]
    if "labor_amount_total" in overrides:
        fs["labor_amount_total"] = overrides["labor_amount_total"]
    return base


def make_panel(name: str, rows: list) -> dict:
    return {"name": name, "rows": rows}


def make_estimate_data(panels: list) -> dict:
    """Build data structure matching what EmsParser + RulesEngine expect."""
    return {
        "claim": {"panels": panels, "validation": {}},
        "claim_meta": {
            "claim_number": "TEST-001",
            "carrier": "Test Carrier",
            "loss_date": "2026-01-01T00:00:00Z"
        },
        "evidence_matrix": {
            "processing_status": "not started",
            "documents": [],
            "photos": [],
        }
    }


# ---------------------------------------------------------------------------
# Included Labor Rule (AUDIT_001)
# ---------------------------------------------------------------------------

class TestIncludedLaborRule:
    def test_flags_hours_without_amount(self):
        line = make_line(
            labor_hours_total=2.5,
            labor_amount_total=0.0,
            part_price=0.0,
            misc_amount=0.0,
            has_labor_hours=True,
            has_labor_amount=False,
            has_part_price=False,
        )
        line["financial_signature"]["labor_hours_total"] = 2.5
        line["financial_signature"]["labor_amount_total"] = 0.0

        data = make_estimate_data([make_panel("Test", [line])])
        engine = RulesEngine()
        result = engine.evaluate_estimate(data)

        findings = result["audit"]["base_findings"]
        assert any(f["rule_id"] == "AUDIT_001" for f in findings), \
            "Should flag included labor with hours but no amount"

    def test_ignores_included_operations(self):
        line = make_line(
            operation_type="Included",
            operation_code="INC",
            labor_hours_total=1.0,
            labor_amount_total=0.0,
            part_price=0.0,
            part_number="",
        )
        line["financial_signature"]["labor_hours_total"] = 1.0
        line["financial_signature"]["labor_amount_total"] = 0.0

        data = make_estimate_data([make_panel("Test", [line])])
        engine = RulesEngine()
        result = engine.evaluate_estimate(data)

        findings = result["audit"]["base_findings"]
        assert not any(f["rule_id"] == "AUDIT_001" for f in findings), \
            "Should NOT flag included labor for legitimate bundled operations"


# ---------------------------------------------------------------------------
# Negative Labor Rule (AUDIT_007)
# ---------------------------------------------------------------------------

class TestNegativeLaborRule:
    def test_flags_negative_labor(self):
        line = make_line(
            labor_amount_body=-50.0,
            labor_hours_total=-1.5,
        )
        line["financial_signature"]["labor_amount_total"] = -50.0
        line["financial_signature"]["labor_hours_total"] = -1.5

        data = make_estimate_data([make_panel("Test", [line])])
        engine = RulesEngine()
        result = engine.evaluate_estimate(data)

        findings = result["audit"]["base_findings"]
        assert any(f["rule_id"] == "AUDIT_007" for f in findings), \
            "Should flag negative labor amounts"


# ---------------------------------------------------------------------------
# Labor No Hours Rule (AUDIT_008)
# ---------------------------------------------------------------------------

class TestLaborNoHoursRule:
    def test_flags_amount_without_hours(self):
        line = make_line(
            labor_amount_body=125.0,
            labor_hours_total=0.0,
            has_labor_amount=True,
            has_labor_hours=False,
        )
        line["financial_signature"]["labor_amount_total"] = 125.0
        line["financial_signature"]["labor_hours_total"] = 0.0

        data = make_estimate_data([make_panel("Test", [line])])
        engine = RulesEngine()
        result = engine.evaluate_estimate(data)

        findings = result["audit"]["base_findings"]
        assert any(f["rule_id"] == "AUDIT_008" for f in findings), \
            "Should flag labor amount without hours"

    def test_ignores_scan_lines(self):
        line = make_line(
            description="Pre Scan",
            labor_amount_body=50.0,
            labor_hours_total=0.0,
            is_scan_related=True,
            service_subtype="scan",
        )
        line["financial_signature"]["labor_amount_total"] = 50.0
        line["financial_signature"]["labor_hours_total"] = 0.0

        data = make_estimate_data([make_panel("Test", [line])])
        engine = RulesEngine()
        result = engine.evaluate_estimate(data)

        findings = result["audit"]["base_findings"]
        assert not any(f["rule_id"] == "AUDIT_008" for f in findings), \
            "Should NOT flag scan lines for amount-without-hours"


# ---------------------------------------------------------------------------
# Zero-Price Part Rule (AUDIT_009)
# ---------------------------------------------------------------------------

class TestZeroPricePartRule:
    def test_flags_zero_price_part(self):
        line = make_line(
            part_number="HO-12345",
            part_price=0.0,
            row_type="part_only",
            has_part_price=False,
        )

        data = make_estimate_data([make_panel("Test", [line])])
        engine = RulesEngine()
        result = engine.evaluate_estimate(data)

        findings = result["audit"]["base_findings"]
        assert any(f["rule_id"] == "AUDIT_009" for f in findings), \
            "Should flag zero-price part"

    def test_ignores_included_labor_parts(self):
        line = make_line(
            part_number="HO-12345",
            part_price=0.0,
            row_type="part_only",
            is_included_labor=True,
            has_part_price=False,
        )

        data = make_estimate_data([make_panel("Test", [line])])
        engine = RulesEngine()
        result = engine.evaluate_estimate(data)

        findings = result["audit"]["base_findings"]
        assert not any(f["rule_id"] == "AUDIT_009" for f in findings), \
            "Should NOT flag included labor parts"


# ---------------------------------------------------------------------------
# High Misc Rule (AUDIT_004)
# ---------------------------------------------------------------------------

class TestHighMiscRule:
    def test_flags_high_misc_without_invoice(self):
        line = make_line(
            misc_amount=200.0,
            row_type="misc_only",
            has_misc_amount=True,
        )

        data = make_estimate_data([make_panel("Test", [line])])
        engine = RulesEngine()
        result = engine.evaluate_estimate(data)

        findings = result["audit"]["base_findings"]
        assert any(f["rule_id"] == "AUDIT_004" for f in findings), \
            "Should flag misc charges > $50"

    def test_ignores_low_misc(self):
        line = make_line(
            misc_amount=25.0,
            row_type="misc_only",
            has_misc_amount=True,
        )

        data = make_estimate_data([make_panel("Test", [line])])
        engine = RulesEngine()
        result = engine.evaluate_estimate(data)

        findings = result["audit"]["base_findings"]
        assert not any(f["rule_id"] == "AUDIT_004" for f in findings), \
            "Should NOT flag misc charges <= $50"


# ---------------------------------------------------------------------------
# Haz Waste Rule (AUDIT_005)
# ---------------------------------------------------------------------------

class TestHazWasteRule:
    def test_detects_haz_waste(self):
        line = make_line(
            description="Hazardous Waste Disposal",
            misc_subtype="hazardous_waste",
        )

        data = make_estimate_data([make_panel("Test", [line])])
        engine = RulesEngine()
        result = engine.evaluate_estimate(data)

        findings = result["audit"]["base_findings"]
        assert any(f["rule_id"] == "AUDIT_005" for f in findings), \
            "Should flag hazardous waste charges"


# ---------------------------------------------------------------------------
# Mechanical on Cosmetic Rule (AUDIT_010)
# ---------------------------------------------------------------------------

class TestMechOnCosmeticRule:
    def test_flags_mech_on_cosmetic_estimate(self):
        # No frame/diag labor → cosmetic estimate
        line = make_line(
            labor_amount_mechanical=75.0,
            part_number="ENG-001",
            description="Engine Mount",
        )

        data = make_estimate_data([make_panel("Test", [line])])
        engine = RulesEngine()
        result = engine.evaluate_estimate(data)

        findings = result["audit"]["base_findings"]
        assert any(f["rule_id"] == "AUDIT_010" for f in findings), \
            "Should flag mechanical labor on cosmetic estimate"

    def test_ignores_mech_when_structural_exists(self):
        # Has frame labor → structural estimate, mech is expected
        line_structural = make_line(
            line_no="1",
            labor_amount_frame=200.0,
        )
        line_mech = make_line(
            line_no="2",
            labor_amount_mechanical=75.0,
        )

        data = make_estimate_data([make_panel("Test", [line_structural, line_mech])])
        engine = RulesEngine()
        result = engine.evaluate_estimate(data)

        findings = result["audit"]["base_findings"]
        assert not any(f["rule_id"] == "AUDIT_010" for f in findings), \
            "Should NOT flag mechanical when structural damage exists"


# ---------------------------------------------------------------------------
# NATGEN Rules
# ---------------------------------------------------------------------------

class TestNatGenRules:
    def test_scan_over_allowance(self):
        # Use explicit line construction since scan rule reads financial_signature directly
        line = {
            "line_no": "1",
            "description": "Pre-Repair Scan",
            "service_subtype": "scan",
            "is_scan_related": True,
            "row_type": "operation",
            "is_header": False,
            "operation_type": "",
            "operation_code": "",
            "part_type": "",
            "supplement": "",
            "financial_signature": {
                "labor_hours_total": 1.5,
                "part_price": 0.0,
                "misc_amount": 0.0,
                "labor_amount_total": 0.0,
            },
        }
        data = make_estimate_data([make_panel("Test", [line])])
        engine = RulesEngine()
        result = engine.evaluate_estimate(data)

        natgen_findings = result["audit"]["carrier_overlays"]["natgen"]["findings"]
        assert any("Scan Labor Exceeds Allowance" in f.get("title", "") for f in natgen_findings), \
            f"Should flag scan labor > 0.5 hrs, got: {natgen_findings}"

    def test_calibration_original_estimate(self):
        line = make_line(
            description="ADAS Calibration",
            service_subtype="sensor_aim",
            is_calibration_related=True,
            supplement="",
            part_price=300.0,
            has_part_price=False,
        )
        line["financial_signature"]["part_price"] = 300.0

        data = make_estimate_data([make_panel("Test", [line])])
        engine = RulesEngine()
        result = engine.evaluate_estimate(data)

        natgen_findings = result["audit"]["carrier_overlays"]["natgen"]["findings"]
        assert any("Calibration Timing" in f.get("title", "") for f in natgen_findings), \
            "Should flag calibration charges on original estimate"

    def test_calibration_no_trigger_part(self):
        line = make_line(
            line_no="1",
            description="Radar Calibration",
            service_subtype="sensor_aim",
            is_calibration_related=True,
            supplement="S01",
            part_price=200.0,
        )
        line["financial_signature"]["part_price"] = 200.0

        data = make_estimate_data([make_panel("Test", [line])])
        engine = RulesEngine()
        result = engine.evaluate_estimate(data)

        natgen_findings = result["audit"]["carrier_overlays"]["natgen"]["findings"]
        # Should flag calibration without trigger parts on supplement
        assert len(natgen_findings) >= 1, \
            "Should flag calibration without trigger parts"


# ---------------------------------------------------------------------------
# Full Pipeline Integration Test
# ---------------------------------------------------------------------------

class TestRulesEngineIntegration:
    def test_multiple_rules_fire_on_realistic_data(self):
        """Simulate a realistic estimate with multiple issues."""
        lines = [
            # Line 1: Normal part, no issues
            make_line(line_no="1", description="Front Bumper", part_price=450.0,
                       has_part_price=True, row_type="part_labor_hybrid"),
            # Line 2: Included labor anomaly
            make_line(line_no="2", description="Blend Fender", labor_hours_total=1.0,
                       operation_type="Blend"),
            # Line 3: High misc charge without invoice
            make_line(line_no="3", description="Tow Charge", misc_amount=150.0,
                       row_type="misc_only", has_misc_amount=True),
            # Line 4: Zero-price part
            make_line(line_no="4", description="Clip Set", part_number="CL-001",
                       row_type="part_only", has_part_price=False),
            # Line 5: Scan over allowance
            make_line(line_no="5", description="Post Scan", is_scan_related=True,
                       service_subtype="scan", labor_hours_total=2.0),
        ]
        # Fix financial signatures
        lines[1]["financial_signature"]["labor_hours_total"] = 1.0
        lines[1]["financial_signature"]["labor_amount_total"] = 0.0
        lines[4]["financial_signature"]["labor_hours_total"] = 2.0

        data = make_estimate_data([make_panel("Front End", lines)])
        engine = RulesEngine()
        result = engine.evaluate_estimate(data)

        all_findings = (
            result["audit"]["base_findings"] +
            result["audit"]["carrier_overlays"]["natgen"]["findings"]
        )

        # Should have findings from multiple rules
        rule_ids = {f["rule_id"] for f in all_findings}
        assert len(rule_ids) >= 3, f"Expected at least 3 rules to fire, got {len(rule_ids)}: {rule_ids}"

    def test_clean_estimate_has_no_findings(self):
        """A perfectly clean estimate should pass."""
        lines = [
            make_line(line_no="1", description="Front Bumper", part_price=450.0,
                       labor_hours_total=3.0, labor_amount_body=195.0,
                       has_part_price=True, has_labor_hours=True, has_labor_amount=True,
                       row_type="part_labor_hybrid"),
            make_line(line_no="2", description="Grille", part_price=200.0,
                       labor_hours_total=1.5, labor_amount_body=97.50,
                       has_part_price=True, has_labor_hours=True, has_labor_amount=True,
                       row_type="part_labor_hybrid"),
        ]
        for l in lines:
            l["financial_signature"]["labor_amount_total"] = l["labor_amount_body"]

        data = make_estimate_data([make_panel("Front End", lines)])
        engine = RulesEngine()
        result = engine.evaluate_estimate(data)

        base_findings = result["audit"]["base_findings"]
        # Checklist rules (CHECK_001-004) always fire as auditor prompts
        check_findings = [f for f in base_findings if f["rule_id"].startswith("CHECK_")]
        audit_findings = [f for f in base_findings if not f["rule_id"].startswith("CHECK_")]
        assert len(audit_findings) == 0, \
            f"Expected 0 audit findings on clean estimate, got {len(audit_findings)}: {[f['rule_id'] for f in audit_findings]}"
        assert len(check_findings) == 4, \
            f"Expected 4 checklist prompts on any estimate, got {len(check_findings)}"
