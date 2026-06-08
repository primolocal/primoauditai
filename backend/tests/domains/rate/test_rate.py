"""Tests for rate domain rules — RATE_001."""
import pytest

from src.domains.rate.rules import ZIPRateVerificationRule
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
        "financial_signature": {
            "part_price": 0.0,
            "labor_amount_total": 0.0,
            "labor_hours_total": 0.0,
        },
    }
    base.update(kwargs)
    return base


class TestZIPRateVerificationRule:
    """RATE_001: Verify labor rates match ZIP code standard."""

    def test_applies_always(self):
        ctx = make_ctx()
        rule = ZIPRateVerificationRule()
        assert rule.applies(ctx) is True

    def test_flags_missing_zip(self):
        ctx = make_ctx(metadata={"shop_address": "123 Main St", "shop_name": "ABC Auto"})
        rule = ZIPRateVerificationRule()
        results = rule.evaluate(ctx)
        assert len(results) == 1
        assert results[0].rule_id == "RATE_001"
        assert results[0].severity == "medium"
        assert "No ZIP code" in results[0].description

    def test_skips_when_no_shop_info(self):
        ctx = make_ctx()
        rule = ZIPRateVerificationRule()
        results = rule.evaluate(ctx)
        assert len(results) == 0

    def test_flags_zip_not_in_database(self):
        ctx = make_ctx(metadata={"shop_address": "123 Main St, Houston, TX 77001"})
        rule = ZIPRateVerificationRule()
        results = rule.evaluate(ctx)
        # lookup_labor is a stub returning None — should flag ZIP not found
        assert len(results) == 1
        assert results[0].severity == "medium"
        assert "77001" in results[0].description

    def test_extracts_zip_from_address(self):
        ctx = make_ctx(metadata={"shop_address": "456 Oak Ave, Dallas, TX 75201-1234"})
        rule = ZIPRateVerificationRule()
        results = rule.evaluate(ctx)
        assert len(results) >= 1
        # Should mention the ZIP
        assert "75201" in results[0].description or "75201" in (results[0].summary or "")

    def test_extracts_zip_before_state(self):
        ctx = make_ctx(metadata={"shop_address": "789 Pine St, 75201 TX"})
        rule = ZIPRateVerificationRule()
        results = rule.evaluate(ctx)
        assert len(results) >= 1
        assert "75201" in results[0].description or "75201" in (results[0].summary or "")
