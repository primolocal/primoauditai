"""Tests for RACED domain rules — RACED_001."""
import pytest

from src.domains.raced.rules import RACEDTransferRule
from src.engine.context import AuditContext


def make_ctx(lines) -> AuditContext:
    return AuditContext(lines=lines, metadata={})


def line(**kwargs):
    base = {
        "line_no": 1,
        "description": "Test",
        "operation_label": "",
        "part_type": "",
        "is_header": False,
    }
    base.update(kwargs)
    return base


class TestRACEDTransferRule:
    """RACED_001: Verify LKQ transfer lines match RACED assembly data."""

    def test_applies_always(self):
        ctx = make_ctx([])
        rule = RACEDTransferRule()
        assert rule.applies(ctx) is True

    def test_no_lkq_parts_no_results(self):
        ctx = make_ctx([
            line(line_no=10, description="Replace fender", operation_label="Replace", part_type="OEM"),
        ])
        rule = RACEDTransferRule()
        results = rule.evaluate(ctx)
        assert len(results) == 0

    def test_verified_transfer_low_severity(self):
        ctx = make_ctx([
            line(line_no=10, description="LKQ door assembly", operation_label="Replace", part_type="LKQ"),
            line(line_no=20, description="R&I door mirror", operation_label="Remove & Install"),
        ])
        rule = RACEDTransferRule()
        results = rule.evaluate(ctx)
        assert len(results) == 1
        assert results[0].rule_id == "RACED_001"
        assert results[0].severity == "low"
        assert "door" in results[0].description.lower()
        assert "mirror" in results[0].description.lower()

    def test_multiple_lkq_assemblies(self):
        ctx = make_ctx([
            line(line_no=10, description="LKQ bumper cover", operation_label="Replace", part_type="LKQ"),
            line(line_no=20, description="R&I bumper bracket", operation_label="Remove & Install"),
            line(line_no=30, description="LKQ hood", operation_label="Replace", part_type="LKQ"),
            line(line_no=40, description="R&I hood insulator", operation_label="Remove & Install"),
        ])
        rule = RACEDTransferRule()
        results = rule.evaluate(ctx)
        assert len(results) == 2
        assert results[0].line_numbers[0] == 20  # bumper bracket
        assert results[1].line_numbers[0] == 40  # hood insulator

    def test_skips_non_transfer_lines(self):
        ctx = make_ctx([
            line(line_no=10, description="LKQ door assembly", operation_label="Replace", part_type="LKQ"),
            line(line_no=20, description="Blend door", operation_label="Blend"),
        ])
        rule = RACEDTransferRule()
        results = rule.evaluate(ctx)
        assert len(results) == 0

    def test_skips_headers(self):
        ctx = make_ctx([
            line(line_no=1, is_header=True, description="Panel: Front Door"),
            line(line_no=10, description="LKQ door", operation_label="Replace", part_type="LKQ"),
            line(line_no=20, description="R&I door handle", operation_label="Remove & Install"),
        ])
        rule = RACEDTransferRule()
        results = rule.evaluate(ctx)
        assert len(results) == 1
        assert results[0].line_numbers == [20]

    def test_lkq_in_description(self):
        ctx = make_ctx([
            line(line_no=10, description="LKQ fender panel", operation_label="Replace"),
            line(line_no=20, description="R&I fender liner", operation_label="Remove & Install"),
        ])
        rule = RACEDTransferRule()
        results = rule.evaluate(ctx)
        assert len(results) == 1
        assert "fender" in results[0].description.lower()
