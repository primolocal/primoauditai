"""Tests for checklist domain rules — CHECK_001 through CHKLST_001."""
import pytest

from src.domains.checklist.rules import (
    CCCAuditorChecklistRule,
    NADARequiredCheckRule,
    OdometerPhotoCheckRule,
    ProductionDateCheckRule,
    VINPhotoCheckRule,
)
from src.engine.context import AuditContext


def make_ctx(lines=None, metadata=None, photos=None) -> AuditContext:
    """Build AuditContext with optional data."""
    return AuditContext(
        lines=lines or [],
        metadata=metadata or {},
        extracted_photos=photos or [],
    )


class TestNADARequiredCheckRule:
    """CHECK_001: NADA Clean Retail printout required."""

    def test_always_applies(self):
        ctx = make_ctx()
        rule = NADARequiredCheckRule()
        assert rule.applies(ctx) is True

    def test_returns_single_result(self):
        ctx = make_ctx()
        rule = NADARequiredCheckRule()
        results = rule.evaluate(ctx)
        assert len(results) == 1
        assert results[0].rule_id == "CHECK_001"
        assert results[0].severity == "high"
        assert results[0].line_numbers == []


class TestVINPhotoCheckRule:
    """CHECK_002: VIN photo required if not already present."""

    def test_applies_when_no_vin_photo(self):
        ctx = make_ctx()
        rule = VINPhotoCheckRule()
        assert rule.applies(ctx) is True

    def test_skips_when_vin_photo_present(self):
        ctx = make_ctx(photos=[{"filename": "vin_dash.jpg", "tags": ["vin"]}])
        rule = VINPhotoCheckRule()
        assert rule.applies(ctx) is False

    def test_returns_single_result(self):
        ctx = make_ctx()
        rule = VINPhotoCheckRule()
        results = rule.evaluate(ctx)
        assert len(results) == 1
        assert results[0].rule_id == "CHECK_002"
        assert "VIN" in results[0].description


class TestOdometerPhotoCheckRule:
    """CHECK_003: Odometer photo required if not already present."""

    def test_applies_when_no_odometer_photo(self):
        ctx = make_ctx()
        rule = OdometerPhotoCheckRule()
        assert rule.applies(ctx) is True

    def test_skips_when_odometer_photo_present(self):
        ctx = make_ctx(photos=[{"filename": "odometer.jpg"}])
        rule = OdometerPhotoCheckRule()
        assert rule.applies(ctx) is False

    def test_skips_when_odo_photo_present(self):
        ctx = make_ctx(photos=[{"filename": "odo_reading.jpg"}])
        rule = OdometerPhotoCheckRule()
        assert rule.applies(ctx) is False

    def test_returns_single_result(self):
        ctx = make_ctx()
        rule = OdometerPhotoCheckRule()
        results = rule.evaluate(ctx)
        assert len(results) == 1
        assert results[0].rule_id == "CHECK_003"


class TestProductionDateCheckRule:
    """CHECK_004: Production date documented."""

    def test_always_applies(self):
        ctx = make_ctx()
        rule = ProductionDateCheckRule()
        assert rule.applies(ctx) is True

    def test_returns_single_result(self):
        ctx = make_ctx()
        rule = ProductionDateCheckRule()
        results = rule.evaluate(ctx)
        assert len(results) == 1
        assert results[0].rule_id == "CHECK_004"
        assert "Production date" in results[0].description


class TestCCCAuditorChecklistRule:
    """CHKLST_001: Complete CCC pre-submission checklist."""

    def test_always_applies(self):
        ctx = make_ctx()
        rule = CCCAuditorChecklistRule()
        assert rule.applies(ctx) is True

    def test_returns_multiple_results(self):
        ctx = make_ctx()
        rule = CCCAuditorChecklistRule()
        results = rule.evaluate(ctx)
        assert len(results) >= 8  # facts, claim type, tabs, inspection, vehicle, estimate, rates, settlements, properties

    def test_hail_claim_hint(self):
        ctx = make_ctx(metadata={"loss_description": "hail damage"})
        rule = CCCAuditorChecklistRule()
        results = rule.evaluate(ctx)
        claim_type = [r for r in results if "claim type" in r.description.lower()]
        assert len(claim_type) == 1
        assert "Hail" in claim_type[0].description

    def test_collision_hint(self):
        ctx = make_ctx(lines=[{"description": "Front bumper collision impact"}])
        rule = CCCAuditorChecklistRule()
        results = rule.evaluate(ctx)
        claim_type = [r for r in results if "claim type" in r.description.lower()]
        assert len(claim_type) == 1
        assert "Collision" in claim_type[0].description

    def test_supplement_inspection_summary(self):
        ctx = make_ctx(metadata={"document_type": "supplement", "shop_name": "ABC Auto", "shop_address": "123 Main St, Houston, TX"})
        rule = CCCAuditorChecklistRule()
        results = rule.evaluate(ctx)
        inspection = [r for r in results if "repair site" in r.description.lower() or "shop:" in r.description.lower()]
        assert len(inspection) == 1
        assert "Supplement" in inspection[0].description

    def test_vehicle_critical_when_missing_data(self):
        ctx = make_ctx(metadata={})
        rule = CCCAuditorChecklistRule()
        results = rule.evaluate(ctx)
        vehicle = [r for r in results if "VIN:" in r.description]
        assert len(vehicle) == 1
        assert vehicle[0].severity == "critical"
        assert "MISSING" in vehicle[0].description

    def test_vehicle_high_when_complete(self):
        ctx = make_ctx(metadata={"vin": "1HGCM82633A123456", "odometer": 45000, "production_date": "01/2023"})
        rule = CCCAuditorChecklistRule()
        results = rule.evaluate(ctx)
        vehicle = [r for r in results if "VIN:" in r.description]
        assert len(vehicle) == 1
        assert vehicle[0].severity == "high"
        assert "MISSING" not in vehicle[0].description

    def test_tl_threshold_lookup(self):
        rule = CCCAuditorChecklistRule()
        assert rule._get_tl_threshold("TX") == "80% Internal"
        assert rule._get_tl_threshold("FL") == "80% Mandated"
        assert rule._get_tl_threshold("CA") == "No Mandate"
        assert rule._get_tl_threshold("") == ""
        assert rule._get_tl_threshold("ZZ") == ""
