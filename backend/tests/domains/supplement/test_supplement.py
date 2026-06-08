"""Tests for supplement domain rules — SUPP_001 through SUPP_005."""
import pytest

from src.domains.supplement.rules import (
    AlternativePartsVerificationRule,
    SupplementAlignmentDocRule,
    SupplementCalibrationDocRule,
    SupplementScanDocRule,
    SupplementSubletDocRule,
)
from src.engine.context import AuditContext


def make_ctx(lines: list, **kwargs) -> AuditContext:
    """Build AuditContext with lines and optional metadata."""
    return AuditContext(lines=lines, metadata=kwargs)


class TestAlternativePartsVerificationRule:
    """SUPP_001: Verify alternative parts on supplement lines meet carrier hierarchy."""

    def test_applies_when_supplement_lines_exist(self):
        ctx = make_ctx([{"line_no": 1, "description": "test", "supplement": "S01"}])
        rule = AlternativePartsVerificationRule()
        assert rule.applies(ctx) is True

    def test_no_alternative_part_no_flag(self):
        ctx = make_ctx([{"line_no": 5, "description": "Replace Hood", "supplement": "S01", "part_number": "123456"}])
        rule = AlternativePartsVerificationRule()
        results = rule.evaluate(ctx)
        assert len(results) == 0

    def test_lkq_part_flagged(self):
        ctx = make_ctx([{"line_no": 10, "description": "LKQ Bumper", "supplement": "S01", "part_number": "LKQ-123"}])
        rule = AlternativePartsVerificationRule()
        results = rule.evaluate(ctx)
        assert len(results) == 1
        assert results[0].rule_id == "SUPP_001"
        assert results[0].line_numbers == [10]

    def test_aftermarket_keyword_flagged(self):
        ctx = make_ctx([{"line_no": 15, "description": "Aftermarket Fender", "supplement": "S01"}])
        rule = AlternativePartsVerificationRule()
        results = rule.evaluate(ctx)
        assert len(results) == 1

    def test_e01_supplement_skipped(self):
        ctx = make_ctx([{"line_no": 20, "description": "LKQ Bumper", "supplement": "E01"}])
        rule = AlternativePartsVerificationRule()
        results = rule.evaluate(ctx)
        assert len(results) == 0

    def test_no_supplement_skipped(self):
        ctx = make_ctx([{"line_no": 25, "description": "LKQ Bumper"}])
        rule = AlternativePartsVerificationRule()
        results = rule.evaluate(ctx)
        assert len(results) == 0


class TestSupplementCalibrationDocRule:
    """SUPP_002: Calibrations on supplements require invoice documentation."""

    def test_calibration_supplement_flagged(self):
        ctx = make_ctx([{"line_no": 30, "description": "Front camera calibration", "supplement": "S02", "part_price": 150}])
        rule = SupplementCalibrationDocRule()
        results = rule.evaluate(ctx)
        assert len(results) == 1
        assert results[0].rule_id == "SUPP_002"
        assert results[0].line_numbers == [30]

    def test_adas_keyword_flagged(self):
        ctx = make_ctx([{"line_no": 35, "description": "ADAS radar aim", "supplement": "S02", "labor_hours": 1.5}])
        rule = SupplementCalibrationDocRule()
        results = rule.evaluate(ctx)
        assert len(results) == 1

    def test_zero_charge_skipped(self):
        ctx = make_ctx([{"line_no": 40, "description": "Front camera calibration", "supplement": "S02"}])
        rule = SupplementCalibrationDocRule()
        results = rule.evaluate(ctx)
        assert len(results) == 0

    def test_no_calibration_keyword_skipped(self):
        ctx = make_ctx([{"line_no": 45, "description": "Replace Hood", "supplement": "S02", "part_price": 200}])
        rule = SupplementCalibrationDocRule()
        results = rule.evaluate(ctx)
        assert len(results) == 0

    def test_e01_skipped(self):
        ctx = make_ctx([{"line_no": 50, "description": "Front camera calibration", "supplement": "E01", "part_price": 150}])
        rule = SupplementCalibrationDocRule()
        results = rule.evaluate(ctx)
        assert len(results) == 0


class TestSupplementScanDocRule:
    """SUPP_003: Scan charges beyond 0.5 allowance require invoice on supplements."""

    def test_scan_over_half_hour_flagged(self):
        ctx = make_ctx([{"line_no": 55, "description": "Full scan", "supplement": "S03", "labor_hours": 1.0}])
        rule = SupplementScanDocRule()
        results = rule.evaluate(ctx)
        assert len(results) == 1
        assert results[0].rule_id == "SUPP_003"

    def test_scan_with_price_flagged(self):
        ctx = make_ctx([{"line_no": 60, "description": "Diagnostic scan", "supplement": "S03", "part_price": 75}])
        rule = SupplementScanDocRule()
        results = rule.evaluate(ctx)
        assert len(results) == 1

    def test_scan_half_hour_no_price_skipped(self):
        ctx = make_ctx([{"line_no": 65, "description": "Quick scan", "supplement": "S03", "labor_hours": 0.5}])
        rule = SupplementScanDocRule()
        results = rule.evaluate(ctx)
        assert len(results) == 0

    def test_scan_under_half_hour_skipped(self):
        ctx = make_ctx([{"line_no": 70, "description": "Quick scan", "supplement": "S03", "labor_hours": 0.3}])
        rule = SupplementScanDocRule()
        results = rule.evaluate(ctx)
        assert len(results) == 0

    def test_no_scan_keyword_skipped(self):
        ctx = make_ctx([{"line_no": 75, "description": "Replace Hood", "supplement": "S03", "labor_hours": 2.0}])
        rule = SupplementScanDocRule()
        results = rule.evaluate(ctx)
        assert len(results) == 0


class TestSupplementAlignmentDocRule:
    """SUPP_004: Wheel alignments on supplements require invoice documentation."""

    def test_alignment_flagged(self):
        ctx = make_ctx([{"line_no": 80, "description": "4 wheel alignment", "supplement": "S04", "labor_hours": 1.2}])
        rule = SupplementAlignmentDocRule()
        results = rule.evaluate(ctx)
        assert len(results) == 1
        assert results[0].rule_id == "SUPP_004"

    def test_align_keyword_flagged(self):
        ctx = make_ctx([{"line_no": 85, "description": "Front end align", "supplement": "S04", "part_price": 100}])
        rule = SupplementAlignmentDocRule()
        results = rule.evaluate(ctx)
        assert len(results) == 1

    def test_zero_charge_skipped(self):
        ctx = make_ctx([{"line_no": 90, "description": "4 wheel alignment", "supplement": "S04"}])
        rule = SupplementAlignmentDocRule()
        results = rule.evaluate(ctx)
        assert len(results) == 0

    def test_no_alignment_keyword_skipped(self):
        ctx = make_ctx([{"line_no": 95, "description": "Replace Hood", "supplement": "S04", "part_price": 200}])
        rule = SupplementAlignmentDocRule()
        results = rule.evaluate(ctx)
        assert len(results) == 0


class TestSupplementSubletDocRule:
    """SUPP_005: ANY sublet on a supplement requires supporting invoice."""

    def test_sublet_flagged(self):
        ctx = make_ctx([{"line_no": 100, "description": "Sublet tow", "supplement": "S05", "part_price": 85}])
        rule = SupplementSubletDocRule()
        results = rule.evaluate(ctx)
        assert len(results) == 1
        assert results[0].rule_id == "SUPP_005"

    def test_tow_keyword_flagged(self):
        ctx = make_ctx([{"line_no": 105, "description": "Tow to shop", "supplement": "S05", "labor_hours": 0.5}])
        rule = SupplementSubletDocRule()
        results = rule.evaluate(ctx)
        assert len(results) == 1

    def test_storage_keyword_flagged(self):
        ctx = make_ctx([{"line_no": 110, "description": "Storage fee", "supplement": "S05", "part_price": 50}])
        rule = SupplementSubletDocRule()
        results = rule.evaluate(ctx)
        assert len(results) == 1

    def test_is_sublet_field_flagged(self):
        ctx = make_ctx([{"line_no": 115, "description": "Glass replacement", "supplement": "S05", "is_sublet": True, "part_price": 300}])
        rule = SupplementSubletDocRule()
        results = rule.evaluate(ctx)
        assert len(results) == 1

    def test_zero_charge_skipped(self):
        ctx = make_ctx([{"line_no": 120, "description": "Sublet tow", "supplement": "S05"}])
        rule = SupplementSubletDocRule()
        results = rule.evaluate(ctx)
        assert len(results) == 0

    def test_e01_skipped(self):
        ctx = make_ctx([{"line_no": 125, "description": "Sublet tow", "supplement": "E01", "part_price": 85}])
        rule = SupplementSubletDocRule()
        results = rule.evaluate(ctx)
        assert len(results) == 0

    def test_no_sublet_no_keyword_skipped(self):
        ctx = make_ctx([{"line_no": 130, "description": "Replace Hood", "supplement": "S05", "part_price": 200}])
        rule = SupplementSubletDocRule()
        results = rule.evaluate(ctx)
        assert len(results) == 0
