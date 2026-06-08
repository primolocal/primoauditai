"""Tests for learning domain rules — LEARN_001."""
import pytest

from src.domains.learning.rules import LowConfidenceReviewRule
from src.engine.context import AuditContext


def make_ctx(lines) -> AuditContext:
    return AuditContext(lines=lines, metadata={})


def line(**kwargs):
    base = {
        "line_no": 1,
        "description": "Test",
        "is_header": False,
        "confidence": 1.0,
    }
    base.update(kwargs)
    return base


class TestLowConfidenceReviewRule:
    """LEARN_001: Human review required for any finding below 95% confidence."""

    def test_applies_always(self):
        ctx = make_ctx([])
        rule = LowConfidenceReviewRule()
        assert rule.applies(ctx) is True

    def test_no_lines_no_results(self):
        ctx = make_ctx([])
        rule = LowConfidenceReviewRule()
        results = rule.evaluate(ctx)
        assert len(results) == 0

    def test_high_confidence_no_result(self):
        ctx = make_ctx([
            line(line_no=10, confidence=1.0),
            line(line_no=20, confidence=0.95),
        ])
        rule = LowConfidenceReviewRule()
        results = rule.evaluate(ctx)
        assert len(results) == 0

    def test_low_confidence_flagged(self):
        ctx = make_ctx([
            line(line_no=10, confidence=0.94),
        ])
        rule = LowConfidenceReviewRule()
        results = rule.evaluate(ctx)
        assert len(results) == 1
        assert results[0].rule_id == "LEARN_001"
        assert results[0].severity == "high"
        assert results[0].line_numbers == [10]
        assert results[0].confidence == 0.94
        assert "94%" in results[0].description

    def test_very_low_confidence(self):
        ctx = make_ctx([
            line(line_no=30, confidence=0.5),
        ])
        rule = LowConfidenceReviewRule()
        results = rule.evaluate(ctx)
        assert len(results) == 1
        assert "50%" in results[0].description

    def test_skips_headers(self):
        ctx = make_ctx([
            line(line_no=1, is_header=True, confidence=0.5),
            line(line_no=10, confidence=0.8),
        ])
        rule = LowConfidenceReviewRule()
        results = rule.evaluate(ctx)
        assert len(results) == 1
        assert results[0].line_numbers == [10]

    def test_mixed_confidence_lines(self):
        ctx = make_ctx([
            line(line_no=10, confidence=0.99),
            line(line_no=20, confidence=0.90),
            line(line_no=30, confidence=0.94),
            line(line_no=40, confidence=1.0),
        ])
        rule = LowConfidenceReviewRule()
        results = rule.evaluate(ctx)
        assert len(results) == 2
        assert sorted([r.line_numbers[0] for r in results]) == [20, 30]
