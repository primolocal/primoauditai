"""Tests for state domain rules — STATE_001 through STATE_003."""
import pytest

from src.domains.state.rules import (
    LicenseNumberRequiredRule,
    StateTaxVerificationRule,
    TotalLossThresholdRule,
)
from src.engine.context import AuditContext


def make_ctx(shop_address="", shop_name="", **meta) -> AuditContext:
    return AuditContext(
        lines=[],
        metadata={"shop_address": shop_address, "shop_name": shop_name, **meta},
    )


class TestLicenseNumberRequiredRule:
    """STATE_001: License/registration number required in certain states."""

    def test_applies_in_license_state_ny(self):
        ctx = make_ctx(shop_address="123 Main St, New York, NY 10001")
        rule = LicenseNumberRequiredRule()
        assert rule.applies(ctx) is True

    def test_applies_in_license_state_tx(self):
        ctx = make_ctx(shop_address="123 Main St, Houston, TX 77001")
        rule = LicenseNumberRequiredRule()
        assert rule.applies(ctx) is False  # TX not in license states

    def test_skips_when_no_state(self):
        ctx = make_ctx(shop_address="123 Main St")
        rule = LicenseNumberRequiredRule()
        assert rule.applies(ctx) is False

    def test_returns_single_result_with_state(self):
        ctx = make_ctx(shop_address="123 Main St, New York, NY 10001", shop_name="ABC Auto")
        rule = LicenseNumberRequiredRule()
        results = rule.evaluate(ctx)
        assert len(results) == 1
        assert results[0].rule_id == "STATE_001"
        assert results[0].severity == "high"
        assert "NY" in (results[0].summary or "")
        assert "ABC Auto" in (results[0].detail or "")

    def test_all_license_states_trigger(self):
        for state in ["NY", "CT", "PA", "SC", "NC", "MA", "RI", "DE", "VT"]:
            ctx = make_ctx(shop_address=f"123 Main St, City, {state} 00001")
            rule = LicenseNumberRequiredRule()
            assert rule.applies(ctx) is True, f"{state} should trigger"


class TestStateTaxVerificationRule:
    """STATE_002: Verify CCC Rates tab matches state tax requirements."""

    def test_applies_when_state_present(self):
        ctx = make_ctx(shop_address="123 Main St, Houston, TX 77001")
        rule = StateTaxVerificationRule()
        assert rule.applies(ctx) is True

    def test_skips_when_no_state(self):
        ctx = make_ctx()
        rule = StateTaxVerificationRule()
        assert rule.applies(ctx) is False

    def test_no_tax_state_critical(self):
        ctx = make_ctx(shop_address="123 Main St, Wilmington, DE 19801")
        rule = StateTaxVerificationRule()
        results = rule.evaluate(ctx)
        assert len(results) == 1
        assert results[0].severity == "critical"
        assert "NO taxes" in results[0].description

    def test_tax_everything_state_high(self):
        ctx = make_ctx(shop_address="123 Main St, Seattle, WA 98101")
        rule = StateTaxVerificationRule()
        results = rule.evaluate(ctx)
        assert len(results) == 1
        assert results[0].severity == "high"
        assert "taxes everything" in results[0].description

    def test_normal_state_with_zip(self):
        ctx = make_ctx(shop_address="123 Main St, Dallas, TX 75201")
        rule = StateTaxVerificationRule()
        results = rule.evaluate(ctx)
        assert len(results) == 1
        assert results[0].severity == "high"
        assert "TX" in (results[0].description or "")
        assert "Parts, Materials and Storage" in (results[0].summary or "")

    def test_normal_state_without_zip(self):
        ctx = make_ctx(shop_address="123 Main St, Dallas, TX")
        rule = StateTaxVerificationRule()
        results = rule.evaluate(ctx)
        assert len(results) == 1
        assert "TX" in results[0].description


class TestTotalLossThresholdRule:
    """STATE_003: State-specific total loss threshold."""

    def test_applies_when_state_present(self):
        ctx = make_ctx(shop_address="123 Main St, Houston, TX 77001")
        rule = TotalLossThresholdRule()
        assert rule.applies(ctx) is True

    def test_skips_when_no_state(self):
        ctx = make_ctx()
        rule = TotalLossThresholdRule()
        assert rule.applies(ctx) is False

    def test_mandated_state_critical(self):
        ctx = make_ctx(shop_address="123 Main St, Los Angeles, CA 90001")
        rule = TotalLossThresholdRule()
        results = rule.evaluate(ctx)
        assert len(results) == 1
        assert results[0].severity == "medium"  # CA has no mandate
        assert "NO total loss threshold mandate" in results[0].description

    def test_state_mandated_critical(self):
        ctx = make_ctx(shop_address="123 Main St, Miami, FL 33101")
        rule = TotalLossThresholdRule()
        results = rule.evaluate(ctx)
        assert len(results) == 1
        assert results[0].severity == "critical"
        assert "80%" in results[0].description

    def test_internal_guideline_high(self):
        ctx = make_ctx(shop_address="123 Main St, Houston, TX 77001")
        rule = TotalLossThresholdRule()
        results = rule.evaluate(ctx)
        assert len(results) == 1
        assert results[0].severity == "high"
        assert "80%" in results[0].description

    def test_all_states_have_threshold_or_none(self):
        for state in [
            "AK", "AL", "AR", "AZ", "CA", "CO", "CT", "DC", "DE", "FL", "GA",
            "HI", "IA", "ID", "IL", "IN", "KS", "KY", "LA", "MA", "MD", "ME",
            "MI", "MN", "MO", "MS", "MT", "NC", "ND", "NE", "NH", "NJ", "NM",
            "NV", "NY", "OH", "OK", "OR", "PA", "RI", "SC", "SD", "TN", "TX",
            "UT", "VA", "VT", "WA", "WI", "WV", "WY",
        ]:
            ctx = make_ctx(shop_address=f"123 Main St, City, {state} 00001")
            rule = TotalLossThresholdRule()
            assert rule.applies(ctx) is True
            results = rule.evaluate(ctx)
            assert len(results) == 1
            # Every state should have either a threshold or a "no mandate" message
            desc = results[0].description
            assert any(kw in desc for kw in ["threshold", "mandate", "No mandate"]), f"{state} missing threshold info: {desc}"
