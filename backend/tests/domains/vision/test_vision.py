"""Tests for vision domain rules — VISION_001, PHOTO_VERIFY_001, VISION_ANALYSIS_001."""
import pytest

from src.domains.vision.rules import (
    PhotoRequirementsRule,
    PhotoVerificationRule,
    VisionAnalysisRule,
)
from src.engine.context import AuditContext


def make_ctx(lines=None, photos=None, metadata=None) -> AuditContext:
    return AuditContext(
        lines=lines or [],
        extracted_photos=photos or [],
        metadata=metadata or {},
    )


def line(**kwargs):
    base = {
        "line_no": 1,
        "description": "Test",
        "operation_label": "Replace",
        "is_header": False,
        "is_included_labor": False,
        "financial_signature": {
            "part_price": 100.0,
            "labor_amount_total": 50.0,
            "labor_hours_total": 1.0,
        },
    }
    base.update(kwargs)
    return base


class TestPhotoRequirementsRule:
    """VISION_001: Comprehensive photo verification checklist."""

    def test_applies_when_photos_present(self):
        ctx = make_ctx(photos=[{"filename": "vin.jpg"}])
        rule = PhotoRequirementsRule()
        assert rule.applies(ctx) is True

    def test_skips_when_no_photos(self):
        ctx = make_ctx()
        rule = PhotoRequirementsRule()
        assert rule.applies(ctx) is False

    def test_returns_required_photo_results(self):
        ctx = make_ctx(photos=[{"filename": "vin.jpg"}])
        rule = PhotoRequirementsRule()
        results = rule.evaluate(ctx)
        assert len(results) >= 8  # 7 required + quality check
        assert all(r.rule_id == "VISION_001" for r in results)

    def test_hail_claim_adds_critical_results(self):
        ctx = make_ctx(
            photos=[{"filename": "hail.jpg"}],
            metadata={"loss_description": "hail damage"},
        )
        rule = PhotoRequirementsRule()
        results = rule.evaluate(ctx)
        hail_results = [r for r in results if r.severity == "critical"]
        assert len(hail_results) >= 2

    def test_photo_quality_check_present(self):
        ctx = make_ctx(photos=[{"filename": "a.jpg"}, {"filename": "b.jpg"}])
        rule = PhotoRequirementsRule()
        results = rule.evaluate(ctx)
        quality = [r for r in results if "clear, well-lit" in (r.description or "")]
        assert len(quality) == 1
        assert "2 photos" in (quality[0].description or "")


class TestPhotoVerificationRule:
    """PHOTO_VERIFY_001: Photo evidence verification for estimate lines."""

    def test_applies_when_photos_present(self):
        ctx = make_ctx(photos=[{"filename": "damage.jpg"}], lines=[line()])
        rule = PhotoVerificationRule()
        assert rule.applies(ctx) is True

    def test_skips_when_no_photos(self):
        ctx = make_ctx(lines=[line()])
        rule = PhotoVerificationRule()
        assert rule.applies(ctx) is False

    def test_returns_results_for_lines_with_photos(self):
        ctx = make_ctx(
            photos=[{"filename": "damage.jpg"}],
            lines=[line(line_no=10, description="Replace fender")],
        )
        rule = PhotoVerificationRule()
        results = rule.evaluate(ctx)
        assert len(results) >= 1
        assert results[0].rule_id == "PHOTO_VERIFY_001"
        assert results[0].line_numbers == [10]

    def test_skips_included_operations(self):
        ctx = make_ctx(
            photos=[{"filename": "damage.jpg"}],
            lines=[line(line_no=5, operation_label="Included", financial_signature={"part_price":0,"labor_amount_total":0})],
        )
        rule = PhotoVerificationRule()
        results = rule.evaluate(ctx)
        assert len(results) == 0


class TestVisionAnalysisRule:
    """VISION_ANALYSIS_001: AI vision analysis on damage photos."""

    def test_applies_when_photos_unanalyzed(self):
        ctx = make_ctx(photos=[{"filename": "damage.jpg"}])
        rule = VisionAnalysisRule()
        assert rule.applies(ctx) is True

    def test_skips_when_photos_already_analyzed(self):
        ctx = make_ctx(photos=[{"filename": "damage.jpg", "ai_damage_type": "dent"}])
        rule = VisionAnalysisRule()
        assert rule.applies(ctx) is False

    def test_skips_when_no_photos(self):
        ctx = make_ctx()
        rule = VisionAnalysisRule()
        assert rule.applies(ctx) is False

    def test_returns_pending_result(self):
        ctx = make_ctx(photos=[{"filename": "a.jpg"}, {"filename": "b.jpg"}])
        rule = VisionAnalysisRule()
        results = rule.evaluate(ctx)
        assert len(results) == 1
        assert results[0].rule_id == "VISION_ANALYSIS_001"
        assert "pending" in results[0].description.lower()
        assert "2 photos" in results[0].description
