"""
Tests for all Tommy's Audit Brain rules.
"""

from src.domains.tommy.rules import (
    AlignmentRequiredRule,
    CoverCarRequiredRule,
    DamageToValueCheckRule,
    EscalationTriggerRule,
    FrameSetupMeasureRule,
    HailWindshieldCausationRule,
    LumpSumDealerInvoiceRule,
    TotalLossThresholdFlagRule,
)
from src.engine.context import AuditContext


class TestCoverCarRequiredRule:
    """PAINT_001."""

    def test_fires_when_refinish_present_and_cover_missing(self) -> None:
        ctx = AuditContext(lines=[
            {"line_no": 1, "description": "Panel repair", "operation_label": "repair"},
            {"line_no": 2, "description": "Refinish hood", "operation_label": "refinish"},
        ])
        rule = CoverCarRequiredRule()
        results = rule.evaluate(ctx)
        assert len(results) == 1
        assert results[0].rule_id == "PAINT_001"

    def test_silent_when_cover_present(self) -> None:
        ctx = AuditContext(lines=[
            {"line_no": 1, "description": "Refinish hood", "operation_label": "refinish"},
            {"line_no": 2, "description": "Cover car", "operation_label": "miscellaneous"},
        ])
        rule = CoverCarRequiredRule()
        results = rule.evaluate(ctx)
        assert len(results) == 0


class TestTotalLossThresholdRule:
    """TL_001."""

    def test_fires_when_estimate_over_5000(self) -> None:
        ctx = AuditContext(lines=[
            {"line_no": 1, "description": "Panel", "total": 3000},
            {"line_no": 2, "description": "Parts", "total": 2500},
        ])
        rule = TotalLossThresholdFlagRule()
        results = rule.evaluate(ctx)
        assert len(results) == 1
        assert results[0].rule_id == "TL_001"
        assert results[0].severity == "high"
        assert "$5,500" in results[0].summary

    def test_critical_severity_when_over_10000(self) -> None:
        ctx = AuditContext(lines=[
            {"line_no": 1, "description": "Major repair", "total": 12000},
        ])
        rule = TotalLossThresholdFlagRule()
        results = rule.evaluate(ctx)
        assert results[0].severity == "critical"

    def test_silent_when_estimate_under_5000(self) -> None:
        ctx = AuditContext(lines=[
            {"line_no": 1, "description": "Small", "total": 1000},
        ])
        rule = TotalLossThresholdFlagRule()
        results = rule.evaluate(ctx)
        assert len(results) == 0


class TestLumpSumDealerInvoiceRule:
    """SUPP_008."""

    def test_fires_when_dealer_invoice_present(self) -> None:
        ctx = AuditContext(lines=[
            {"line_no": 1, "description": "Dealer invoice for bumper", "supplement": "S01", "is_header": False},
        ])
        rule = LumpSumDealerInvoiceRule()
        results = rule.evaluate(ctx)
        assert len(results) == 1
        assert results[0].rule_id == "SUPP_008"

    def test_ignores_header_lines(self) -> None:
        ctx = AuditContext(lines=[
            {"line_no": 1, "description": "Dealer invoice", "supplement": "S01", "is_header": True},
        ])
        rule = LumpSumDealerInvoiceRule()
        results = rule.evaluate(ctx)
        assert len(results) == 0

    def test_silent_when_no_dealer_lines(self) -> None:
        ctx = AuditContext(lines=[
            {"line_no": 1, "description": "Regular labor", "supplement": "S01", "is_header": False},
        ])
        rule = LumpSumDealerInvoiceRule()
        results = rule.evaluate(ctx)
        assert len(results) == 0


class TestFrameSetupMeasureRule:
    """FRAME_001."""

    def test_fires_when_frame_present_and_setup_missing(self) -> None:
        ctx = AuditContext(lines=[
            {"line_no": 1, "description": "Frame rail repair"},
            {"line_no": 2, "description": "Panel repair"},
        ])
        rule = FrameSetupMeasureRule()
        results = rule.evaluate(ctx)
        assert len(results) == 1
        assert results[0].rule_id == "FRAME_001"

    def test_silent_when_setup_present(self) -> None:
        ctx = AuditContext(lines=[
            {"line_no": 1, "description": "Frame rail repair"},
            {"line_no": 2, "description": "Set-up and measure frame"},
        ])
        rule = FrameSetupMeasureRule()
        results = rule.evaluate(ctx)
        assert len(results) == 0

    def test_silent_when_no_frame(self) -> None:
        ctx = AuditContext(lines=[
            {"line_no": 1, "description": "Panel repair"},
        ])
        rule = FrameSetupMeasureRule()
        results = rule.evaluate(ctx)
        assert len(results) == 0


class TestAlignmentRequiredRule:
    """ALIGN_001."""

    def test_fires_when_tire_present_and_align_missing(self) -> None:
        ctx = AuditContext(lines=[
            {"line_no": 1, "description": "Tire replacement"},
        ])
        rule = AlignmentRequiredRule()
        results = rule.evaluate(ctx)
        assert len(results) == 1
        assert results[0].rule_id == "ALIGN_001"

    def test_silent_when_alignment_present(self) -> None:
        ctx = AuditContext(lines=[
            {"line_no": 1, "description": "Tire replacement"},
            {"line_no": 2, "description": "Wheel alignment"},
        ])
        rule = AlignmentRequiredRule()
        results = rule.evaluate(ctx)
        assert len(results) == 0

    def test_silent_on_hail_claims(self) -> None:
        """Hail claims skip alignment check — tire/wheel is R&I for access."""
        ctx = AuditContext(
            lines=[{"line_no": 1, "description": "Tire R&I"}],
            metadata={"loss_description": "Hail damage"},
        )
        rule = AlignmentRequiredRule()
        assert rule.applies(ctx) is False  # engine skips non-applicable rules
        results = rule.evaluate(ctx)
        # Even if evaluate were called directly, it would fire — but engine guards with applies()
        assert results  # prove the rule logic WOULD fire if not for applies() guard

    def test_fires_on_non_hail_collision(self) -> None:
        """Non-hail claims with tire damage DO fire."""
        ctx = AuditContext(
            lines=[{"line_no": 1, "description": "Tire replacement"}],
            metadata={"loss_description": "Collision"},
        )
        rule = AlignmentRequiredRule()
        assert rule.applies(ctx) is True
        results = rule.evaluate(ctx)
        assert len(results) == 1


class TestDamageToValueCheckRule:
    """CHECK_006."""

    def test_fires_when_estimate_over_3000(self) -> None:
        ctx = AuditContext(lines=[
            {"line_no": 1, "description": "Repair", "total": 3500},
        ])
        rule = DamageToValueCheckRule()
        results = rule.evaluate(ctx)
        assert len(results) == 1
        assert results[0].rule_id == "CHECK_006"
        assert "damage-to-value" in results[0].summary.lower()

    def test_silent_when_estimate_under_3000(self) -> None:
        ctx = AuditContext(lines=[
            {"line_no": 1, "description": "Small", "total": 500},
        ])
        rule = DamageToValueCheckRule()
        results = rule.evaluate(ctx)
        assert len(results) == 0


class TestHailWindshieldCausationRule:
    """HAIL_002."""

    def test_fires_on_hail_claim_with_windshield_replace(self) -> None:
        ctx = AuditContext(
            lines=[{"line_no": 1, "description": "Windshield replace"}],
            metadata={"loss_description": "Hail damage"},
        )
        rule = HailWindshieldCausationRule()
        results = rule.evaluate(ctx)
        assert len(results) == 1
        assert results[0].rule_id == "HAIL_002"

    def test_silent_when_not_hail(self) -> None:
        ctx = AuditContext(
            lines=[{"line_no": 1, "description": "Windshield replace"}],
            metadata={"loss_description": "Collision"},
        )
        rule = HailWindshieldCausationRule()
        assert rule.applies(ctx) is False
        results = rule.evaluate(ctx)
        assert results  # would fire if not for applies() guard

    def test_silent_when_no_windshield(self) -> None:
        ctx = AuditContext(
            lines=[{"line_no": 1, "description": "Panel repair"}],
            metadata={"loss_description": "Hail damage"},
        )
        rule = HailWindshieldCausationRule()
        results = rule.evaluate(ctx)
        assert len(results) == 0


class TestEscalationTriggerRule:
    """ESCALATE_001."""

    def test_fires_when_estimate_over_10000(self) -> None:
        ctx = AuditContext(lines=[
            {"line_no": 1, "description": "Major", "total": 12000},
        ])
        rule = EscalationTriggerRule()
        results = rule.evaluate(ctx)
        assert len(results) == 1
        assert results[0].rule_id == "ESCALATE_001"

    def test_high_severity_when_over_15000(self) -> None:
        ctx = AuditContext(lines=[
            {"line_no": 1, "description": "Major", "total": 18000},
        ])
        rule = EscalationTriggerRule()
        results = rule.evaluate(ctx)
        assert results[0].severity == "high"

    def test_silent_when_estimate_under_10000(self) -> None:
        ctx = AuditContext(lines=[
            {"line_no": 1, "description": "Small", "total": 5000},
        ])
        rule = EscalationTriggerRule()
        results = rule.evaluate(ctx)
        assert len(results) == 0
