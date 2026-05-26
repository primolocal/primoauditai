"""
Pre-Submission Checklist Rules — prompts the auditor to verify items that
cannot be fully automated. Auditor confirms yes/no and the answer is logged.
"""
from typing import List
from audit_context import AuditContext
from rules.base import BaseRule, RuleResult


class NADARequiredCheckRule(BaseRule):
    """
    Prompts auditor: Is NADA Clean Retail printout attached? What's the value?
    NatGen requires NADA on ALL files — repairable AND total loss.
    """
    rule_id = "CHECK_001"
    title = "NADA Clean Retail — Attached?"
    category = "documentation_readiness"
    severity = "high"

    def applies(self, ctx: AuditContext) -> bool:
        return True

    def evaluate(self, ctx: AuditContext) -> List[RuleResult]:
        return [RuleResult(
            rule_id=self.rule_id,
            title=self.title,
            category=self.category,
            severity=self.severity,
            affected_lines=[],
            summary="Is the NADA Clean Retail Value printout attached to this file?",
            why_flagged=(
                "NatGen requires NADA Clean Retail printout on ALL files — "
                "repairable AND total loss. No exceptions. "
                "Enter the NADA Clean Retail value below."
            ),
            recommended_actions="Attach NADA printout. Enter Clean Retail value in the notes.",
            status="unreviewed",
            debug_context={"requires_nada": True, "requires_value": True}
        )]


class VINPhotoCheckRule(BaseRule):
    """
    Prompts auditor: Is the VIN photo present and readable?
    VIN from dashboard mandatory. Door VIN required if dash not readable.
    """
    rule_id = "CHECK_002"
    title = "VIN Photo — Present & Readable?"
    category = "documentation_readiness"
    severity = "high"

    def applies(self, ctx: AuditContext) -> bool:
        return True

    def evaluate(self, ctx: AuditContext) -> List[RuleResult]:
        return [RuleResult(
            rule_id=self.rule_id,
            title=self.title,
            category=self.category,
            severity=self.severity,
            affected_lines=[],
            summary="Is the VIN photo present and readable? (Dashboard VIN required. Door VIN if dash not readable.)",
            why_flagged=(
                "NatGen/IANet requires VIN photo on every assignment. "
                "Dashboard VIN mandatory. Door jamb VIN additionally required "
                "if dash photo is not clearly readable."
            ),
            recommended_actions="Confirm VIN photo present. If dash VIN unclear, add door jamb VIN photo.",
            status="unreviewed",
            debug_context={"requires_vin_photo": True}
        )]


class OdometerPhotoCheckRule(BaseRule):
    """
    Prompts auditor: Is the odometer photo present?
    If odometer unavailable, confirm alternative documentation (oil change sticker, owner statement, VIN history).
    """
    rule_id = "CHECK_003"
    title = "Odometer Photo — Present?"
    category = "documentation_readiness"
    severity = "high"

    def applies(self, ctx: AuditContext) -> bool:
        return True

    def evaluate(self, ctx: AuditContext) -> List[RuleResult]:
        return [RuleResult(
            rule_id=self.rule_id,
            title=self.title,
            category=self.category,
            severity=self.severity,
            affected_lines=[],
            summary="Is the odometer/mileage photo present? If not, is alternative documentation attached?",
            why_flagged=(
                "NatGen/IANet requires odometer photo on every assignment. "
                "If odometer cannot be photographed: document oil change sticker, "
                "last known mileage from owner, or VIN history report."
            ),
            recommended_actions=(
                "Confirm odometer photo present. If unavailable, attach alternative: "
                "oil change sticker photo, owner statement, or VIN history mileage."
            ),
            status="unreviewed",
            debug_context={"requires_odometer_photo": True}
        )]


class ProductionDateCheckRule(BaseRule):
    """
    Prompts auditor: Is the production date documented?
    Production date photo mandatory per NatGen. Must appear in appraisal report.
    """
    rule_id = "CHECK_004"
    title = "Production Date — Documented?"
    category = "documentation_readiness"
    severity = "high"

    def applies(self, ctx: AuditContext) -> bool:
        return True

    def evaluate(self, ctx: AuditContext) -> List[RuleResult]:
        return [RuleResult(
            rule_id=self.rule_id,
            title=self.title,
            category=self.category,
            severity=self.severity,
            affected_lines=[],
            summary="Is the vehicle production date documented with photo and in the appraisal report?",
            why_flagged=(
                "NatGen/IANet requires production date on all estimates. "
                "Production date photo is mandatory. Appraisal report must include production date."
            ),
            recommended_actions="Confirm production date photo present and included in appraisal report.",
            status="unreviewed",
            debug_context={"requires_production_date": True}
        )]


# ---------------------------------------------------------------------------
# CCC Auditor Checklist — merged from auditor_checklist.py
# ---------------------------------------------------------------------------

class CCCAuditorChecklistRule(BaseRule):
    """
    CHKLST_001: Complete CCC pre-submission verification.
    Grouped by CCC tab for efficient auditor workflow.
    """
    rule_id = "CHKLST_001"
    title = "CCC Pre-Submission Checklist"
    category = "documentation_readiness"
    severity = "high"

    def applies(self, ctx: AuditContext) -> bool:
        return True

    def evaluate(self, ctx: AuditContext) -> List[RuleResult]:
        results = []
        meta = ctx.raw_data.get("claim_meta", {})
        shop = meta.get("shop", {})
        vehicle = meta.get("vehicle", {})
        panels = ctx.raw_data.get("claim", {}).get("panels", [])

        # Detect supplement vs original
        is_supplement = ctx.is_supplement()

        # Count line items
        total_lines = sum(len(p.get("rows", [])) for p in panels)
        refinish_count = sum(
            1 for p in panels for r in p.get("rows", [])
            if str(r.get("operation_label", "")).lower() in ("refinish",)
        )

        # --- FACTS OF LOSS ---
        results.append(RuleResult(
            rule_id=self.rule_id, title="Facts of Loss — Verify",
            category="documentation_readiness", severity="high",
            affected_lines=[], summary="Verify facts of loss match assignment",
            why_flagged="Confirm date of loss, type of loss, and claim description match the assignment sheet.",
            recommended_actions="Check assignment tab. Verify loss date, loss type, and facts match.",
            status="unreviewed",
        ))

        # --- CLAIM TYPE / DEDUCTIBLE ---
        claim_type_hint = ""
        if ctx.is_hail_claim():
            claim_type_hint = " (Hail/PDR detected in estimate)"
        else:
            panels_text = " ".join(
                r.get("description", "") for p in panels for r in p.get("rows", [])
            ).lower()
            if any(kw in panels_text for kw in ["collision", "impact"]):
                claim_type_hint = " (Collision damage detected)"

        results.append(RuleResult(
            rule_id=self.rule_id, title="Claim Type / Deductible — Verify",
            category="documentation_readiness", severity="high",
            affected_lines=[], summary=f"Verify claim type and deductible{claim_type_hint}",
            why_flagged=(
                "Confirm claim type (Comp/Collision/Liability) and deductible "
                "match the assignment. Incorrect claim type causes coverage issues."
            ),
            recommended_actions="Check Contacts/Insurance tab. Verify type of loss and deductible.",
            status="unreviewed",
        ))

        # --- CCC TABS ---
        results.append(RuleResult(
            rule_id=self.rule_id, title="CCC Tabs — All Complete",
            category="documentation_readiness", severity="high",
            affected_lines=[], summary="Verify all CCC tabs are complete and accurate",
            why_flagged="Every CCC tab must be reviewed before locking. Missing tabs trigger revisions.",
            recommended_actions=(
                "Review: Contacts, Insurance, Inspection, Vehicle, Estimate, "
                "Rates, Settlements, Estimate Properties. Verify each tab."
            ),
            status="unreviewed",
        ))

        # --- CONTACTS / INSURANCE ---
        results.append(RuleResult(
            rule_id=self.rule_id, title="Contacts / Insurance — Verify",
            category="documentation_readiness", severity="high",
            affected_lines=[], summary="Verify contact type and insurance type of loss/deductible",
            why_flagged="Correct contact type, insurance carrier, type of loss, and deductible must match assignment.",
            recommended_actions="Open Contacts and Insurance tabs. Verify all fields match the assignment sheet.",
            status="unreviewed",
        ))

        # --- INSPECTION ---
        shop_name = shop.get("name", "")
        shop_address = shop.get("address", "")
        shop_state = ctx.shop_state()

        if is_supplement and shop_name:
            inspection_summary = f"Supplement — shop: {shop_name} ({shop_state}). Verify repair site listed."
        elif shop_name:
            inspection_summary = f"Shop: {shop_name} ({shop_state}). Verify inspection location."
        else:
            inspection_summary = "No shop listed — verify Owner's Choice or shop info."

        results.append(RuleResult(
            rule_id=self.rule_id, title="Inspection — Verify",
            category="documentation_readiness", severity="high",
            affected_lines=[], summary=inspection_summary,
            why_flagged=(
                "Inspection location must be accurate (home/shop/tow lot). "
                "If supplement, shop MUST be listed. If no shop, use Owner's Choice. "
                "Days to repair must be calculated."
            ),
            recommended_actions=(
                "Verify inspection location: " + (shop_name or "Owner's Choice") + ". "
                "Confirm days to repair input. On supplements, shop ID is mandatory."
            ),
            status="unreviewed",
        ))

        # --- VEHICLE ---
        vin = vehicle.get("vin", "?")
        odo = vehicle.get("mileage", "?")
        prod_date = meta.get("production_date", "?")
        vehicle_state = ctx.shop_state() or meta.get("state", "?")

        missing_vehicle = []
        if vin == "?" or not vin:
            missing_vehicle.append("VIN")
        if odo == "?" or not odo:
            missing_vehicle.append("Odometer")
        if prod_date == "?" or not prod_date:
            missing_vehicle.append("Production Date")

        vehicle_summary = (
            f"VIN: {vin} | Odo: {odo} | Prod: {prod_date} | State: {vehicle_state}"
        )
        if missing_vehicle:
            vehicle_summary += f" — MISSING: {', '.join(missing_vehicle)}"

        results.append(RuleResult(
            rule_id=self.rule_id, title="Vehicle Info — Verify",
            category="documentation_readiness",
            severity="critical" if missing_vehicle else "high",
            affected_lines=[], summary=vehicle_summary,
            why_flagged=(
                "Vehicle VIN, odometer, production date, color, license plate, "
                "state, primary point of impact, condition, impact notes, and "
                "prior damage notes must all be verified." +
                (f" MISSING: {', '.join(missing_vehicle)}." if missing_vehicle else "")
            ),
            recommended_actions=(
                "Open Vehicle tab. Verify all fields: VIN, odometer, production date, "
                "color, license plate/state, POI, condition, impact notes, prior damage notes."
            ),
            status="unreviewed",
        ))

        # --- ESTIMATE (Audit Report) ---
        results.append(RuleResult(
            rule_id=self.rule_id, title="Estimate / Audit Report — Complete",
            category="documentation_readiness", severity="high",
            affected_lines=[], summary=f"Verify estimate ({total_lines} lines) and audit report complete",
            why_flagged=(
                f"Estimate has {total_lines} line items. Audit report must be complete "
                f"with detailed inspection notes, open items, supplement estimate, "
                f"and repair methodology explanation."
            ),
            recommended_actions="Complete audit report. Note open items and supplement estimates.",
            status="unreviewed",
        ))

        # --- RATES ---
        results.append(RuleResult(
            rule_id=self.rule_id, title="Rates — Verify Labor Rates & Tax",
            category="carrier_compliance", severity="high",
            affected_lines=[], summary=f"Verify labor rates and tax config for {vehicle_state or 'state'}",
            why_flagged=(
                "Labor rates must not be overridden. Tax must match ZIP code. "
                "Sales tax boxes must be checked for correct categories per state guidelines. "
                "Hero & Altavara handle tax at profile level — do not manually adjust."
            ),
            recommended_actions=(
                "Open Rates tab. Verify labor rates. Confirm tax rate matches ZIP. "
                "Check sales tax boxes for correct categories. Do NOT overrule labor rates."
            ),
            status="unreviewed",
        ))

        # --- SETTLEMENTS ---
        results.append(RuleResult(
            rule_id=self.rule_id, title="Settlements — Repairable / Total Loss",
            category="carrier_compliance",
            severity="high" if total_lines > 0 else "medium",
            affected_lines=[], summary="Verify settlement type (repairable vs total loss)",
            why_flagged=(
                "If repairable: verify repair cost vs value. Write 100% of damages. "
                "If total loss: NADA Clean Retail required. POI = 15. Settlement = Total Loss. "
                "Document towing, storage, teardown fees and daily storage rate."
            ),
            recommended_actions=(
                "Check Settlements tab. If total loss: POI=15, Settlement=Total Loss. "
                "Attach NADA. Document all advanced charges."
            ),
            status="unreviewed",
        ))

        # --- ESTIMATE PROPERTIES ---
        tl_threshold = self._get_tl_threshold(ctx.shop_state())
        results.append(RuleResult(
            rule_id=self.rule_id, title="Estimate Properties — Verify",
            category="carrier_compliance", severity="high",
            affected_lines=[], summary=(
                f"Verify refinish threshold, materials threshold, TL threshold"
                + (f" ({tl_threshold})" if tl_threshold else "")
            ),
            why_flagged=(
                "Estimate Properties must have correct refinish threshold, "
                "materials threshold, and total loss threshold configured. "
                "Profile must be changed BEFORE any estimate work begins."
            ),
            recommended_actions=(
                "Open Estimate Properties. Verify refinish and materials thresholds. "
                "Confirm total loss threshold matches state/carrier requirements."
                + (f" Current state TL: {tl_threshold}." if tl_threshold else "")
            ),
            status="unreviewed",
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
