"""
Tests for core audit rules (AUDIT_001, AUDIT_004-010).
"""

from src.domains.audit.rules import (
    FlexAddRule,
    HazWasteRule,
    HighMiscRule,
    IncludedLaborRule,
    LaborNoHoursRule,
    MechOnCosmeticRule,
    NegativeLaborRule,
    ZeroPricePartRule,
)
from src.engine.context import AuditContext


def make_line(**kwargs):
    """Factory for estimate lines."""
    base = {
        "line_no": 1,
        "description": "Test Part",
        "operation_label": "Replace",
        "operation_type": "Replace",
        "operation_code": "RPL",
        "part_type": "OEM",
        "part_number": "ABC-123",
        "row_type": "operation",
        "is_header": False,
        "is_included_labor": False,
        "misc_subtype": "",
        "financial_signature": {
            "part_price": 0.0,
            "misc_amount": 0.0,
            "labor_amount_total": 0.0,
            "labor_hours_total": 0.0,
        },
    }
    base.update(kwargs)
    return base


class TestIncludedLaborRule:
    """AUDIT_001."""

    def test_flags_hours_without_amount(self) -> None:
        line = make_line(
            line_no=2,
            description="Panel repair",
            operation_type="Repair",
            operation_code="RPR",
            financial_signature={"labor_hours_total": 2.5, "labor_amount_total": 0.0, "part_price": 0.0, "misc_amount": 0.0},
        )
        ctx = AuditContext(lines=[line])
        rule = IncludedLaborRule()
        results = rule.evaluate(ctx)
        assert len(results) == 1
        assert results[0].rule_id == "AUDIT_001"

    def test_ignores_exempt_operations(self) -> None:
        line = make_line(
            line_no=1,
            description="Blend fender",
            operation_type="Blend",
            operation_code="BLN",
            financial_signature={"labor_hours_total": 1.0, "labor_amount_total": 0.0, "part_price": 0.0, "misc_amount": 0.0},
        )
        ctx = AuditContext(lines=[line])
        rule = IncludedLaborRule()
        results = rule.evaluate(ctx)
        assert len(results) == 0

    def test_silent_when_amount_present(self) -> None:
        line = make_line(
            financial_signature={"labor_hours_total": 2.0, "labor_amount_total": 100.0, "part_price": 0.0, "misc_amount": 0.0},
        )
        ctx = AuditContext(lines=[line])
        rule = IncludedLaborRule()
        results = rule.evaluate(ctx)
        assert len(results) == 0


class TestHighMiscRule:
    """AUDIT_004."""

    def test_flags_high_misc(self) -> None:
        line = make_line(row_type="misc_only", financial_signature={"misc_amount": 200.0})
        ctx = AuditContext(lines=[line])
        rule = HighMiscRule()
        results = rule.evaluate(ctx)
        assert len(results) == 1
        assert results[0].rule_id == "AUDIT_004"

    def test_ignores_low_misc(self) -> None:
        line = make_line(row_type="misc_only", financial_signature={"misc_amount": 25.0})
        ctx = AuditContext(lines=[line])
        rule = HighMiscRule()
        results = rule.evaluate(ctx)
        assert len(results) == 0

    def test_ignores_non_misc_rows(self) -> None:
        line = make_line(row_type="operation", financial_signature={"misc_amount": 200.0})
        ctx = AuditContext(lines=[line])
        rule = HighMiscRule()
        results = rule.evaluate(ctx)
        assert len(results) == 0


class TestHazWasteRule:
    """AUDIT_005."""

    def test_detects_haz_waste(self) -> None:
        line = make_line(description="Hazardous Waste Disposal", misc_subtype="hazardous_waste")
        ctx = AuditContext(lines=[line])
        rule = HazWasteRule()
        results = rule.evaluate(ctx)
        assert len(results) == 1
        assert results[0].rule_id == "AUDIT_005"

    def test_detects_by_description(self) -> None:
        line = make_line(description="Haz waste disposal fee")
        ctx = AuditContext(lines=[line])
        rule = HazWasteRule()
        results = rule.evaluate(ctx)
        assert len(results) == 1

    def test_silent_when_no_haz(self) -> None:
        line = make_line(description="Regular labor")
        ctx = AuditContext(lines=[line])
        rule = HazWasteRule()
        results = rule.evaluate(ctx)
        assert len(results) == 0


class TestFlexAddRule:
    """AUDIT_006."""

    def test_detects_flex_additive(self) -> None:
        line = make_line(description="Flex additive for bumper", misc_subtype="flex_additive")
        ctx = AuditContext(lines=[line])
        rule = FlexAddRule()
        results = rule.evaluate(ctx)
        assert len(results) == 1
        assert results[0].rule_id == "AUDIT_006"

    def test_silent_when_no_flex(self) -> None:
        line = make_line(description="Regular paint")
        ctx = AuditContext(lines=[line])
        rule = FlexAddRule()
        results = rule.evaluate(ctx)
        assert len(results) == 0


class TestNegativeLaborRule:
    """AUDIT_007."""

    def test_flags_negative_labor(self) -> None:
        line = make_line(
            financial_signature={"labor_amount_total": -50.0, "labor_hours_total": -1.5},
        )
        ctx = AuditContext(lines=[line])
        rule = NegativeLaborRule()
        results = rule.evaluate(ctx)
        assert len(results) == 1
        assert results[0].rule_id == "AUDIT_007"
        assert results[0].severity == "high"

    def test_skips_overlap_lines(self) -> None:
        line = make_line(
            description="Overlap deduction",
            operation_label="Overlap",
            financial_signature={"labor_amount_total": -30.0, "labor_hours_total": 0.0},
        )
        ctx = AuditContext(lines=[line])
        rule = NegativeLaborRule()
        results = rule.evaluate(ctx)
        assert len(results) == 0

    def test_skips_small_adjustments(self) -> None:
        line = make_line(
            financial_signature={"labor_amount_total": -10.0, "labor_hours_total": 0.0},
        )
        ctx = AuditContext(lines=[line])
        rule = NegativeLaborRule()
        results = rule.evaluate(ctx)
        assert len(results) == 0

    def test_skips_legitimate_codes(self) -> None:
        line = make_line(
            operation_code="ovl",
            financial_signature={"labor_amount_total": -100.0, "labor_hours_total": -2.0},
        )
        ctx = AuditContext(lines=[line])
        rule = NegativeLaborRule()
        results = rule.evaluate(ctx)
        assert len(results) == 0


class TestLaborNoHoursRule:
    """AUDIT_008."""

    def test_flags_amount_without_hours(self) -> None:
        line = make_line(
            description="Labor charge",
            financial_signature={"labor_amount_total": 125.0, "labor_hours_total": 0.0},
        )
        ctx = AuditContext(lines=[line])
        rule = LaborNoHoursRule()
        results = rule.evaluate(ctx)
        assert len(results) == 1
        assert results[0].rule_id == "AUDIT_008"

    def test_skips_scan_lines(self) -> None:
        line = make_line(
            description="Pre Scan",
            financial_signature={"labor_amount_total": 50.0, "labor_hours_total": 0.0},
        )
        ctx = AuditContext(lines=[line])
        rule = LaborNoHoursRule()
        results = rule.evaluate(ctx)
        assert len(results) == 0

    def test_skips_flat_rate(self) -> None:
        line = make_line(
            description="Transport vehicle",
            financial_signature={"labor_amount_total": 75.0, "labor_hours_total": 0.0},
        )
        ctx = AuditContext(lines=[line])
        rule = LaborNoHoursRule()
        results = rule.evaluate(ctx)
        assert len(results) == 0

    def test_skips_small_no_op(self) -> None:
        line = make_line(
            description="Small fee",
            operation_label="",
            operation_code="",
            financial_signature={"labor_amount_total": 50.0, "labor_hours_total": 0.0},
        )
        ctx = AuditContext(lines=[line])
        rule = LaborNoHoursRule()
        results = rule.evaluate(ctx)
        assert len(results) == 0


class TestZeroPricePartRule:
    """AUDIT_009."""

    def test_flags_zero_price_part(self) -> None:
        line = make_line(
            part_number="HO-12345",
            part_price=0.0,
            row_type="part_only",
            financial_signature={"part_price": 0.0, "misc_amount": 0.0},
        )
        ctx = AuditContext(lines=[line])
        rule = ZeroPricePartRule()
        results = rule.evaluate(ctx)
        assert len(results) == 1
        assert results[0].rule_id == "AUDIT_009"

    def test_ignores_included_labor(self) -> None:
        line = make_line(
            part_number="HO-12345",
            part_price=0.0,
            row_type="part_only",
            is_included_labor=True,
            financial_signature={"part_price": 0.0, "misc_amount": 0.0},
        )
        ctx = AuditContext(lines=[line])
        rule = ZeroPricePartRule()
        results = rule.evaluate(ctx)
        assert len(results) == 0

    def test_ignores_non_part_rows(self) -> None:
        line = make_line(
            part_number="HO-12345",
            part_price=0.0,
            row_type="operation",
            financial_signature={"part_price": 0.0, "misc_amount": 0.0},
        )
        ctx = AuditContext(lines=[line])
        rule = ZeroPricePartRule()
        results = rule.evaluate(ctx)
        assert len(results) == 0


class TestMechOnCosmeticRule:
    """AUDIT_010."""

    def test_flags_mech_on_cosmetic(self) -> None:
        line = make_line(
            description="Engine mount",
            labor_amount_mechanical=75.0,
        )
        ctx = AuditContext(lines=[line])
        rule = MechOnCosmeticRule()
        results = rule.evaluate(ctx)
        assert len(results) == 1
        assert results[0].rule_id == "AUDIT_010"

    def test_silent_when_structural_present(self) -> None:
        lines = [
            make_line(description="Frame rail", labor_amount_frame=200.0),
            make_line(description="Engine mount", labor_amount_mechanical=75.0),
        ]
        ctx = AuditContext(lines=lines)
        rule = MechOnCosmeticRule()
        results = rule.evaluate(ctx)
        assert len(results) == 0

    def test_silent_when_no_mech(self) -> None:
        line = make_line(description="Panel repair", labor_amount_body=50.0)
        ctx = AuditContext(lines=[line])
        rule = MechOnCosmeticRule()
        results = rule.evaluate(ctx)
        assert len(results) == 0
