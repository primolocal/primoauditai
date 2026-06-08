"""Tests for MOTOR domain rules — MOTOR_001."""
import pytest

from src.domains.motor.rules import MOTORIncludedRIRule
from src.engine.context import AuditContext


def make_ctx(lines) -> AuditContext:
    return AuditContext(lines=lines, metadata={})


def line(**kwargs):
    base = {
        "line_no": 1,
        "description": "Test",
        "operation_label": "",
        "is_header": False,
        "is_included_labor": False,
        "financial_signature": {
            "part_price": 0.0,
            "labor_amount_total": 0.0,
            "labor_hours_total": 0.0,
        },
    }
    base.update(kwargs)
    return base


class TestMOTORIncludedRIRule:
    """MOTOR_001: Smart R&I check using MOTOR P-page knowledge."""

    def test_applies_always(self):
        ctx = make_ctx([])
        rule = MOTORIncludedRIRule()
        assert rule.applies(ctx) is True

    def test_included_ri_skipped_when_parent_replace_exists(self):
        """R&I of hood hinge is included when hood replace exists."""
        ctx = make_ctx([
            line(line_no=10, description="Replace hood", operation_label="Replace"),
            line(line_no=20, description="R&I hood hinge", operation_label="Remove & Install"),
        ])
        rule = MOTORIncludedRIRule()
        results = rule.evaluate(ctx)
        # Should be empty because hinge R&I is included in hood replace
        assert len(results) == 0

    def test_unrelated_ri_flagged_when_no_parent(self):
        """R&I of fender liner flagged when no fender operation exists."""
        ctx = make_ctx([
            line(line_no=30, description="R&I fender liner", operation_label="Remove & Install"),
        ])
        rule = MOTORIncludedRIRule()
        results = rule.evaluate(ctx)
        assert len(results) == 1
        assert results[0].rule_id == "MOTOR_001"
        assert results[0].line_numbers == [30]

    def test_headliner_drop_flagged_high(self):
        """Headliner drop is not allowed by NatGen — must be full R&I."""
        ctx = make_ctx([
            line(line_no=10, description="PDR roof", operation_label="PDR"),
            line(line_no=20, description="R&I headliner drop", operation_label="Remove & Install"),
        ])
        rule = MOTORIncludedRIRule()
        results = rule.evaluate(ctx)
        headliner = [r for r in results if "DROP" in (r.description or "")]
        assert len(headliner) == 1
        assert headliner[0].severity == "high"

    def test_pdr_context_skips_trim_ri(self):
        """Hail PDR claims skip trim/lamp/molding R&I as access."""
        ctx = make_ctx([
            line(line_no=10, description="PDR hood", operation_label="PDR"),
            line(line_no=20, description="R&I hood insulator", operation_label="Remove & Install"),
        ])
        rule = MOTORIncludedRIRule()
        results = rule.evaluate(ctx)
        assert len(results) == 0

    def test_repair_parent_justifies_low_confidence(self):
        """R&I justified when repair exists on same panel — low severity."""
        ctx = make_ctx([
            line(line_no=10, description="Repair door", operation_label="Repair"),
            line(line_no=20, description="R&I door handle", operation_label="Remove & Install"),
        ])
        rule = MOTORIncludedRIRule()
        results = rule.evaluate(ctx)
        assert len(results) == 1
        assert results[0].severity == "low"
        assert results[0].confidence == 0.3

    def test_no_justification_medium_confidence(self):
        """R&I with no matching parent gets medium severity."""
        ctx = make_ctx([
            line(line_no=10, description="R&I trunk carpet", operation_label="Remove & Install"),
        ])
        rule = MOTORIncludedRIRule()
        results = rule.evaluate(ctx)
        assert len(results) == 1
        assert results[0].severity == "medium"
        assert results[0].confidence == 0.6

    def test_skips_headers(self):
        ctx = make_ctx([
            line(line_no=1, is_header=True, description="Panel: Front Bumper"),
            line(line_no=5, description="Replace bumper", operation_label="Replace"),
            line(line_no=10, description="R&I bumper bracket", operation_label="Remove & Install"),
        ])
        rule = MOTORIncludedRIRule()
        results = rule.evaluate(ctx)
        # Bracket is included in bumper replace — header should not interfere
        assert len(results) == 0

    def test_included_operations_list_comprehensive(self):
        """Verify key MOTOR included pairs are handled."""
        pairs = [
            ("Replace hood", "R&I hood insulator"),
            ("Replace door", "R&I door mirror"),
            ("Replace bumper", "R&I bumper bracket"),
            ("Replace fender", "R&I fender liner"),
            ("Replace roof", "R&I roof antenna"),
            ("Replace quarter", "R&I quarter molding"),
        ]
        for parent_desc, child_desc in pairs:
            ctx = make_ctx([
                line(line_no=10, description=parent_desc, operation_label="Replace"),
                line(line_no=20, description=child_desc, operation_label="Remove & Install"),
            ])
            rule = MOTORIncludedRIRule()
            results = rule.evaluate(ctx)
            assert len(results) == 0, f"{parent_desc} -> {child_desc} should be included"
