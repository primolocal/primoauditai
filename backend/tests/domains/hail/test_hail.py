"""Tests for hail domain rules — HAIL_001."""
import pytest

from src.domains.hail.rules import PDRIncreaseVerificationRule
from src.engine.context import AuditContext


def make_ctx(lines) -> AuditContext:
    return AuditContext(lines=lines, metadata={})


def line(**kwargs):
    base = {
        "line_no": 1,
        "description": "Test",
        "operation_label": "",
        "is_header": False,
        "financial_signature": {
            "part_price": 0.0,
            "labor_amount_total": 0.0,
            "labor_hours_total": 0.0,
        },
    }
    base.update(kwargs)
    return base


class TestPDRIncreaseVerificationRule:
    """HAIL_001: Verify PDR amounts against Dent Wizard matrix."""

    def test_applies_always(self):
        ctx = make_ctx([])
        rule = PDRIncreaseVerificationRule()
        assert rule.applies(ctx) is True

    def test_flags_pdr_with_price(self):
        ctx = make_ctx([
            line(line_no=10, description="PDR hood", operation_label="PDR", financial_signature={"part_price": 250.0}),
        ])
        rule = PDRIncreaseVerificationRule()
        results = rule.evaluate(ctx)
        assert len(results) == 1
        assert results[0].rule_id == "HAIL_001"
        assert results[0].line_numbers == [10]
        assert "$250.00" in results[0].description

    def test_skips_pdr_with_zero_price(self):
        ctx = make_ctx([
            line(line_no=10, description="PDR hood", operation_label="PDR", financial_signature={"part_price": 0.0}),
        ])
        rule = PDRIncreaseVerificationRule()
        results = rule.evaluate(ctx)
        assert len(results) == 0

    def test_flags_markup_percentage(self):
        ctx = make_ctx([
            line(line_no=20, description="PDR fender +25%", operation_label="PDR", financial_signature={"part_price": 300.0}),
        ])
        rule = PDRIncreaseVerificationRule()
        results = rule.evaluate(ctx)
        assert len(results) == 1
        assert "+25%" in results[0].description
        assert "markup" in results[0].description.lower()

    def test_skips_non_pdr_lines(self):
        ctx = make_ctx([
            line(line_no=10, description="Replace hood", operation_label="Replace", financial_signature={"part_price": 500.0}),
        ])
        rule = PDRIncreaseVerificationRule()
        results = rule.evaluate(ctx)
        assert len(results) == 0

    def test_skips_headers(self):
        ctx = make_ctx([
            line(line_no=1, is_header=True, description="Panel: Hood"),
        ])
        rule = PDRIncreaseVerificationRule()
        results = rule.evaluate(ctx)
        assert len(results) == 0

    def test_multiple_pdr_lines(self):
        ctx = make_ctx([
            line(line_no=10, description="PDR hood", operation_label="PDR", financial_signature={"part_price": 150.0}),
            line(line_no=20, description="PDR fender", operation_label="PDR", financial_signature={"part_price": 200.0}),
            line(line_no=30, description="Replace bumper", operation_label="Replace", financial_signature={"part_price": 0.0}),
        ])
        rule = PDRIncreaseVerificationRule()
        results = rule.evaluate(ctx)
        assert len(results) == 2
        assert sorted([r.line_numbers[0] for r in results]) == [10, 20]
