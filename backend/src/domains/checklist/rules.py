"""Pre-Submission Checklist Rules — prompts the auditor to verify items that
cannot be fully automated. Auditor confirms yes/no and the answer is logged.
"""
from __future__ import annotations

from src.engine.base import BaseRule, RuleResult
from src.engine.context import AuditContext


class NADARequiredCheckRule(BaseRule):
    """CHECK_001: Is NADA Clean Retail printout attached? NatGen requires NADA on ALL files."""
    rule_id = "CHECK_001"
    category = "documentation_readiness"
    severity = "high"

    def applies(self, ctx: AuditContext) -> bool:
        return True

    def evaluate(self, ctx: AuditContext) -> list[RuleResult]:
        return [RuleResult(
            rule_id=self.rule_id,
            category=self.category,
            severity=self.severity,
            description="NADA Clean Retail printout required — verify attached and value entered.",
            line_numbers=[],
        )]


class VINPhotoCheckRule(BaseRule):
    """CHECK_002: Is the VIN photo present and readable? Dashboard VIN mandatory."""
    rule_id = "CHECK_002"
    category = "documentation_readiness"
    severity = "high"

    def applies(self, ctx: AuditContext) -> bool:
        # Skip if VIN photo already detected in extracted photos
        photos = ctx.extracted_photos
        has_vin = any(
            "vin" in str(p.get("filename", "")).lower() or
            "vin" in str(p.get("tags", [])).lower()
            for p in photos
        )
        return not has_vin

    def evaluate(self, ctx: AuditContext) -> list[RuleResult]:
        return [RuleResult(
            rule_id=self.rule_id,
            category=self.category,
            severity=self.severity,
            description="VIN photo required — dashboard VIN mandatory, door jamb if dash not readable.",
            line_numbers=[],
        )]


class OdometerPhotoCheckRule(BaseRule):
    """CHECK_003: Is the odometer photo present? Alternative docs accepted if unavailable."""
    rule_id = "CHECK_003"
    category = "documentation_readiness"
    severity = "high"

    def applies(self, ctx: AuditContext) -> bool:
        # Skip if odometer photo already detected
        photos = ctx.extracted_photos
        has_odo = any(
            "odo" in str(p.get("filename", "")).lower() or
            "odometer" in str(p.get("filename", "")).lower() or
            "odo" in str(p.get("tags", [])).lower()
            for p in photos
        )
        return not has_odo

    def evaluate(self, ctx: AuditContext) -> list[RuleResult]:
        return [RuleResult(
            rule_id=self.rule_id,
            category=self.category,
            severity=self.severity,
            description="Odometer photo required — oil change sticker or owner statement if unavailable.",
            line_numbers=[],
        )]


class ProductionDateCheckRule(BaseRule):
    """CHECK_004: Is the production date documented with photo and in appraisal report?"""
    rule_id = "CHECK_004"
    category = "documentation_readiness"
    severity = "high"

    def applies(self, ctx: AuditContext) -> bool:
        return True

    def evaluate(self, ctx: AuditContext) -> list[RuleResult]:
        return [RuleResult(
            rule_id=self.rule_id,
            category=self.category,
            severity=self.severity,
            description="Production date required — photo mandatory, must appear in appraisal report.",
            line_numbers=[],
        )]


class CCCAuditorChecklistRule(BaseRule):
    """CHKLST_001: Complete CCC pre-submission verification checklist."""
    rule_id = "CHKLST_001"
    category = "documentation_readiness"
    severity = "high"

    def applies(self, ctx: AuditContext) -> bool:
        return True

    def evaluate(self, ctx: AuditContext) -> list[RuleResult]:
        results = []
        meta = ctx.metadata
        shop_address = meta.get("shop_address", "")
        vehicle = {
            "vin": meta.get("vin", ""),
            "mileage": meta.get("odometer", ""),
            "production_date": meta.get("production_date", ""),
        }
        total_lines = len(ctx.lines)

        # --- FACTS OF LOSS ---
        results.append(RuleResult(
            rule_id=self.rule_id,
            category="documentation_readiness",
            severity="high",
            description="Verify facts of loss match assignment — date, type, and claim description.",
            line_numbers=[],
        ))

        # --- CLAIM TYPE / DEDUCTIBLE ---
        claim_type_hint = ""
        if ctx.is_hail_claim():
            claim_type_hint = " (Hail/PDR detected)"
        else:
            descs = " ".join(str(line.get("description", "")).lower() for line in ctx.lines)
            if any(kw in descs for kw in ["collision", "impact"]):
                claim_type_hint = " (Collision damage detected)"
        results.append(RuleResult(
            rule_id=self.rule_id,
            category="documentation_readiness",
            severity="high",
            description=f"Verify claim type and deductible match assignment.{claim_type_hint}",
            line_numbers=[],
        ))

        # --- CCC TABS ---
        results.append(RuleResult(
            rule_id=self.rule_id,
            category="documentation_readiness",
            severity="high",
            description="Verify all CCC tabs are complete: Contacts, Insurance, Inspection, Vehicle, Estimate, Rates, Settlements, Estimate Properties.",
            line_numbers=[],
        ))

        # --- INSPECTION ---
        shop_state = ctx.shop_state() or "?"
        is_supplement = ctx.is_supplement()
        shop_name = meta.get("shop_name", "")
        if is_supplement and shop_name:
            inspection_summary = f"Supplement — shop: {shop_name} ({shop_state}). Verify repair site listed."
        elif shop_name:
            inspection_summary = f"Shop: {shop_name} ({shop_state}). Verify inspection location."
        else:
            inspection_summary = "No shop listed — verify Owner's Choice or shop info."
        results.append(RuleResult(
            rule_id=self.rule_id,
            category="documentation_readiness",
            severity="high",
            description=inspection_summary,
            line_numbers=[],
        ))

        # --- VEHICLE ---
        missing_vehicle = []
        if not vehicle["vin"]:
            missing_vehicle.append("VIN")
        if not vehicle["mileage"]:
            missing_vehicle.append("Odometer")
        if not vehicle["production_date"]:
            missing_vehicle.append("Production Date")
        vehicle_summary = f"VIN: {vehicle['vin'] or '?'} | Odo: {vehicle['mileage'] or '?'} | Prod: {vehicle['production_date'] or '?'} | State: {shop_state}"
        if missing_vehicle:
            vehicle_summary += f" — MISSING: {', '.join(missing_vehicle)}"
        results.append(RuleResult(
            rule_id=self.rule_id,
            category="documentation_readiness",
            severity="critical" if missing_vehicle else "high",
            description=vehicle_summary,
            line_numbers=[],
        ))

        # --- ESTIMATE ---
        results.append(RuleResult(
            rule_id=self.rule_id,
            category="documentation_readiness",
            severity="high",
            description=f"Verify estimate ({total_lines} lines) and audit report are complete with inspection notes and open items.",
            line_numbers=[],
        ))

        # --- RATES ---
        results.append(RuleResult(
            rule_id=self.rule_id,
            category="carrier_compliance",
            severity="high",
            description=f"Verify labor rates and tax config for {shop_state}. Do NOT override labor rates.",
            line_numbers=[],
        ))

        # --- SETTLEMENTS ---
        results.append(RuleResult(
            rule_id=self.rule_id,
            category="carrier_compliance",
            severity="high" if total_lines > 0 else "medium",
            description="Verify settlement type (repairable vs total loss). Total loss requires NADA and POI=15.",
            line_numbers=[],
        ))

        # --- ESTIMATE PROPERTIES ---
        tl_threshold = self._get_tl_threshold(shop_state)
        results.append(RuleResult(
            rule_id=self.rule_id,
            category="carrier_compliance",
            severity="high",
            description=f"Verify refinish threshold, materials threshold, and total loss threshold ({tl_threshold}).",
            line_numbers=[],
        ))

        return results

    @staticmethod
    def _get_tl_threshold(state: str) -> str:
        thresholds = {
            "AK": "80% Internal", "AL": "75% Mandated", "AR": "70% Mandated",
            "AZ": "80% Internal", "CA": "No Mandate", "CO": "80% Internal",
            "CT": "No Mandate", "DC": "75% Mandated", "DE": "80% Mandated",
            "FL": "80% Mandated", "GA": "80% Internal", "HI": "75% Internal",
            "IA": "80% Internal", "ID": "80% Internal", "IL": "80% Internal",
            "IN": "80% Internal", "KS": "75% Mandated", "KY": "75% Mandated",
            "LA": "75% Mandated", "MA": "No Mandate", "MD": "75% Mandated",
            "ME": "80% Internal", "MI": "75% Mandated", "MN": "80% Mandated",
            "MO": "80% Mandated", "MS": "75% Mandated", "MT": "80% Internal",
            "NC": "75% Mandated", "ND": "75% Mandated", "NE": "75% Mandated",
            "NH": "75% Mandated", "NJ": "80% Internal", "NM": "80% Internal",
            "NV": "65% Mandated", "NY": "75% - 8yr newer", "OH": "75% Internal",
            "OK": "60% Mandated", "OR": "80% Internal", "PA": "80% Internal",
            "RI": "75% Mandated", "SC": "75% Mandated", "SD": "80% Internal",
            "TN": "75% Mandated", "TX": "80% Internal", "UT": "Est+Salvage>ACV",
            "VA": "75% Mandated", "VT": "80% Internal", "WA": "80% Internal",
            "WI": "70% - 7yr newer", "WV": "75% Mandated", "WY": "75% Mandated",
        }
        return thresholds.get(state.upper() if state else "", "")
