"""Tests for deductible domain rules — CHECK_005."""
import pytest

from src.domains.deductible.rules import DeductibleRequiredRule
from src.engine.context import AuditContext


def make_ctx(lines=None, metadata=None) -> AuditContext:
    return AuditContext(
        lines=lines or [],
        metadata=metadata or {},
    )


def line(**kwargs):
    base = {
        "line_no": 1,
        "description": "Test",
        "is_header": False,
        "row_type": "operation",
    }
    base.update(kwargs)
    return base


class TestDeductibleRequiredRule:
    """CHECK_005: Collision/Comprehensive estimates must show deductible."""

    def test_applies_always(self):
        ctx = make_ctx()
        rule = DeductibleRequiredRule()
        assert rule.applies(ctx) is True

    def test_no_loss_type_no_result(self):
        ctx = make_ctx()
        rule = DeductibleRequiredRule()
        results = rule.evaluate(ctx)
        assert len(results) == 0

    def test_collision_without_deductible_flagged(self):
        ctx = make_ctx(
            metadata={"loss_type": "collision"},
            lines=[line(line_no=10, description="Replace fender")],
        )
        rule = DeductibleRequiredRule()
        results = rule.evaluate(ctx)
        assert len(results) == 1
        assert results[0].rule_id == "CHECK_005"
        assert results[0].severity == "high"
        assert "deductible" in results[0].description.lower()

    def test_collision_with_deductible_no_result(self):
        ctx = make_ctx(
            metadata={"loss_type": "collision"},
            lines=[line(line_no=10, description="deductible $500")],
        )
        rule = DeductibleRequiredRule()
        results = rule.evaluate(ctx)
        assert len(results) == 0

    def test_comprehensive_without_deductible_flagged(self):
        ctx = make_ctx(
            metadata={"loss_type": "comprehensive"},
            lines=[line(line_no=10, description="Repair roof")],
        )
        rule = DeductibleRequiredRule()
        results = rule.evaluate(ctx)
        assert len(results) == 1
        assert "comprehensive" in results[0].description.lower()

    def test_non_collision_no_result(self):
        ctx = make_ctx(
            metadata={"loss_type": "liability"},
            lines=[line(line_no=10, description="Replace bumper")],
        )
        rule = DeductibleRequiredRule()
        results = rule.evaluate(ctx)
        assert len(results) == 0

    def test_deductible_row_type_no_result(self):
        ctx = make_ctx(
            metadata={"loss_type": "collision"},
            lines=[line(line_no=99, description="Deductible", row_type="deductible")],
        )
        rule = DeductibleRequiredRule()
        results = rule.evaluate(ctx)
        assert len(results) == 0

    def test_comp_variant_no_result(self):
        ctx = make_ctx(
            metadata={"type_of_loss": "comp"},
            lines=[line(line_no=10, description="deductible applied")],
        )
        rule = DeductibleRequiredRule()
        results = rule.evaluate(ctx)
        assert len(results) == 0
