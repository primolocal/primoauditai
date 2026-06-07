"""
Tests for NatGen carrier rules (NATGEN_001-022).
Critical false-positive fixes from v1 are explicitly tested.
"""

from src.domains.natgen.rules import (
    CalibrationChargeTimingRule,
    CalibrationTriggerSupportRule,
    ExcessivePaintScopeRule,
    NoFlexAdditiveRule,
    NoLKQSuspensionRule,
    OEMPartRestrictionRule,
    SafetySystemLKQRule,
    ScanLaborThresholdRule,
    ShopInfoRule,
    TotalLossWriteFullRule,
    UnjustifiedReplaceRule,
)
from src.engine.context import AuditContext


def line(**kwargs):
    base = {
        "line_no": 1,
        "description": "Test",
        "operation_label": "",
        "operation_type": "",
        "operation_code": "",
        "part_type": "",
        "part_number": "",
        "row_type": "operation",
        "is_header": False,
        "is_sublet": False,
        "is_included_labor": False,
        "service_subtype": "",
        "supplement": "",
        "panel_name": "",
        "financial_signature": {
            "part_price": 0.0,
            "misc_amount": 0.0,
            "labor_amount_total": 0.0,
            "labor_hours_total": 0.0,
        },
    }
    base.update(kwargs)
    return base


class TestScanLaborThreshold:
    """NATGEN_001: 0.5hr max, scan invoice required."""

    def test_flags_scan_over_half_hour(self) -> None:
        ctx = AuditContext(lines=[
            line(description="Pre-Repair Scan", service_subtype="scan", financial_signature={"labor_hours_total": 1.5}),
        ])
        rule = ScanLaborThresholdRule()
        results = rule.evaluate(ctx)
        assert len(results) == 1  # hours violation only (no dollar charge on this line)
        assert any("1.5 hours" in (r.summary or "") for r in results)

    def test_allows_half_hour_scan(self) -> None:
        ctx = AuditContext(lines=[
            line(description="Pre Scan", service_subtype="scan", financial_signature={"labor_hours_total": 0.5}),
        ])
        rule = ScanLaborThresholdRule()
        results = rule.evaluate(ctx)
        assert len(results) == 0

    def test_flags_scan_with_dollar_amount(self) -> None:
        ctx = AuditContext(lines=[
            line(description="Post Scan", service_subtype="scan", financial_signature={"misc_amount": 75.0}),
        ])
        rule = ScanLaborThresholdRule()
        results = rule.evaluate(ctx)
        assert any("missing" in r.summary.lower() for r in results)


class TestCalibrationTiming:
    """NATGEN_002: No calibration charges on original estimate."""

    def test_flags_calibration_on_original(self) -> None:
        ctx = AuditContext(lines=[
            line(description="ADAS Calibration", service_subtype="sensor_aim", supplement="E01", financial_signature={"part_price": 300.0}),
        ])
        rule = CalibrationChargeTimingRule()
        results = rule.evaluate(ctx)
        assert len(results) == 1
        assert "E01" in results[0].summary

    def test_silent_when_no_charge(self) -> None:
        ctx = AuditContext(lines=[
            line(description="ADAS Calibration", service_subtype="sensor_aim", supplement="E01", financial_signature={"part_price": 0.0}),
        ])
        rule = CalibrationChargeTimingRule()
        results = rule.evaluate(ctx)
        assert len(results) == 0


class TestCalibrationTriggerSupport:
    """NATGEN_003: Calibration needs trigger parts."""

    def test_silent_with_strong_trigger(self) -> None:
        ctx = AuditContext(lines=[
            line(line_no=1, description="ADAS Calibration", service_subtype="sensor_aim", financial_signature={"part_price": 200.0}),
            line(line_no=2, description="Bumper cover replace"),
        ])
        rule = CalibrationTriggerSupportRule()
        results = rule.evaluate(ctx)
        assert len(results) == 0

    def test_flags_without_trigger(self) -> None:
        ctx = AuditContext(lines=[
            line(line_no=1, description="ADAS Calibration", service_subtype="sensor_aim", financial_signature={"part_price": 200.0}),
        ])
        rule = CalibrationTriggerSupportRule()
        results = rule.evaluate(ctx)
        assert len(results) == 1
        assert results[0].severity == "high"

    def test_excludes_headlight(self) -> None:
        """Headlight lines should NOT trigger calibration detection."""
        ctx = AuditContext(lines=[
            line(description="Headlight calibration", service_subtype="sensor_aim", financial_signature={"part_price": 100.0}),
        ])
        # Headlight is excluded from _is_calibration_line
        # So no calibration lines detected → no results
        rule = CalibrationTriggerSupportRule()
        results = rule.evaluate(ctx)
        assert len(results) == 0


class TestOEMRestriction:
    """NATGEN_004: OEM only current year + <15K miles."""

    def test_flags_old_year(self) -> None:
        ctx = AuditContext(
            lines=[line(description="OEM Hood", part_type="OEM", financial_signature={"part_price": 450.0})],
            metadata={"vehicle": {"year": 2022, "mileage": 5000}},
        )
        rule = OEMPartRestrictionRule()
        results = rule.evaluate(ctx)
        assert len(results) == 1
        assert "2022" in results[0].summary

    def test_flags_high_mileage(self) -> None:
        ctx = AuditContext(
            lines=[line(description="OEM Fender", part_type="OEM", financial_signature={"part_price": 300.0})],
            metadata={"vehicle": {"year": 2026, "mileage": 20000}},
        )
        rule = OEMPartRestrictionRule()
        results = rule.evaluate(ctx)
        assert len(results) == 1
        assert "20,000" in results[0].summary

    def test_silent_for_lkq(self) -> None:
        ctx = AuditContext(
            lines=[line(description="LKQ Door", part_type="LKQ", financial_signature={"part_price": 150.0})],
            metadata={"vehicle": {"year": 2022, "mileage": 5000}},
        )
        rule = OEMPartRestrictionRule()
        results = rule.evaluate(ctx)
        assert len(results) == 0


class TestUnjustifiedReplace:
    """NATGEN_006: Default to repair."""

    def test_flags_replace_on_bumper(self) -> None:
        ctx = AuditContext(lines=[
            line(description="Front bumper cover", operation_label="replace", part_type="LKQ"),
        ])
        rule = UnjustifiedReplaceRule()
        results = rule.evaluate(ctx)
        assert len(results) == 1

    def test_skips_corrosion(self) -> None:
        ctx = AuditContext(lines=[
            line(description="Corrosion protection", operation_label="replace"),
        ])
        rule = UnjustifiedReplaceRule()
        results = rule.evaluate(ctx)
        assert len(results) == 0


class TestExcessivePaintScope:
    """NATGEN_012: 3+ refinish panels flagged."""

    def test_flags_three_panels(self) -> None:
        ctx = AuditContext(lines=[
            line(description="Hood refinish", operation_label="refinish", panel_name="Hood"),
            line(description="Fender refinish", operation_label="refinish", panel_name="Fender"),
            line(description="Door refinish", operation_label="refinish", panel_name="Door"),
        ])
        rule = ExcessivePaintScopeRule()
        results = rule.evaluate(ctx)
        assert len(results) == 1
        assert "3 panels" in results[0].summary

    def test_silent_under_three(self) -> None:
        ctx = AuditContext(lines=[
            line(description="Hood refinish", operation_label="refinish", panel_name="Hood"),
            line(description="Fender refinish", operation_label="refinish", panel_name="Fender"),
        ])
        rule = ExcessivePaintScopeRule()
        results = rule.evaluate(ctx)
        assert len(results) == 0


class TestSafetySystemLKQ:
    """NATGEN_016: No LKQ on safety systems."""

    def test_flags_airbag_lkq(self) -> None:
        ctx = AuditContext(lines=[
            line(description="Driver airbag", part_type="LKQ", financial_signature={"part_price": 400.0}),
        ])
        rule = SafetySystemLKQRule()
        results = rule.evaluate(ctx)
        assert len(results) == 1
        assert "airbag" in results[0].summary.lower()

    def test_silent_for_oem_safety(self) -> None:
        ctx = AuditContext(lines=[
            line(description="Driver airbag", part_type="OEM", financial_signature={"part_price": 400.0}),
        ])
        rule = SafetySystemLKQRule()
        results = rule.evaluate(ctx)
        assert len(results) == 0


class TestNoLKQSuspension:
    """NATGEN_015: No LKQ suspension."""

    def test_flags_strut_lkq(self) -> None:
        ctx = AuditContext(lines=[
            line(description="Front strut", part_type="LKQ", financial_signature={"part_price": 120.0}),
        ])
        rule = NoLKQSuspensionRule()
        results = rule.evaluate(ctx)
        assert len(results) == 1

    def test_silent_for_nonsuspension(self) -> None:
        ctx = AuditContext(lines=[
            line(description="LKQ Door", part_type="LKQ", financial_signature={"part_price": 150.0}),
        ])
        rule = NoLKQSuspensionRule()
        results = rule.evaluate(ctx)
        assert len(results) == 0


class TestTotalLossWriteFull:
    """NATGEN_022: Total loss — write everything."""

    def test_fires_over_10000(self) -> None:
        ctx = AuditContext(lines=[
            line(description="Major repair", total=12000.0),
        ])
        rule = TotalLossWriteFullRule()
        assert rule.applies(ctx) is True
        results = rule.evaluate(ctx)
        assert len(results) == 1

    def test_not_applies_under_10000(self) -> None:
        ctx = AuditContext(lines=[
            line(description="Small", financial_signature={"labor_amount_total": 5000.0}),
        ])
        rule = TotalLossWriteFullRule()
        assert rule.applies(ctx) is False


class TestShopInfo:
    """NATGEN_011: Shop info required."""

    def test_flags_missing_name(self) -> None:
        ctx = AuditContext(metadata={"shop": {"address": "123 Main", "phone": "555-1234"}})
        rule = ShopInfoRule()
        results = rule.evaluate(ctx)
        assert len(results) == 1
        assert "shop name" in results[0].summary

    def test_silent_when_complete(self) -> None:
        ctx = AuditContext(metadata={"shop": {"name": "ABC Body", "address": "123 Main", "phone": "555-1234"}})
        rule = ShopInfoRule()
        results = rule.evaluate(ctx)
        assert len(results) == 0


class TestNoFlexAdditive:
    """NATGEN_014: Flex only on plastic panels."""

    def test_flags_flex_on_metal(self) -> None:
        ctx = AuditContext(lines=[
            line(description="Flex additive", panel_name="Hood"),
        ])
        rule = NoFlexAdditiveRule()
        results = rule.evaluate(ctx)
        assert len(results) == 1

    def test_silent_on_bumper(self) -> None:
        ctx = AuditContext(lines=[
            line(description="Flex additive", panel_name="Front Bumper"),
        ])
        rule = NoFlexAdditiveRule()
        results = rule.evaluate(ctx)
        assert len(results) == 0
