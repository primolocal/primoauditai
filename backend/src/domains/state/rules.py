"""State-specific rules — triggers based on shop/inspection location state.
Covers license/registration requirements and tax configuration.
"""
from __future__ import annotations

from src.engine.base import BaseRule, RuleResult
from src.engine.context import AuditContext


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

STATE_TL_THRESHOLDS = {
    "AK": ("80%", "Internal"), "AL": ("75%", "State Mandated"),
    "AR": ("70%", "State Mandated"), "AZ": ("80%", "Internal"),
    "CA": (None, "No State Mandate"), "CO": ("80%", "Internal"),
    "CT": (None, "No State Mandate"), "DC": ("75%", "State Mandated"),
    "DE": ("80%", "State Mandated"), "FL": ("80%", "State Mandated"),
    "GA": ("80%", "Internal"), "HI": ("75%", "Internal"),
    "IA": ("80%", "Internal"), "ID": ("80%", "Internal"),
    "IL": ("80%", "Internal"), "IN": ("80%", "Internal"),
    "KS": ("75%", "State Mandated"), "KY": ("75%", "State Mandated"),
    "LA": ("75%", "State Mandated"), "MA": (None, "No State Mandate"),
    "MD": ("75%", "State Mandated"), "ME": ("80%", "Internal"),
    "MI": ("75%", "State Mandated"), "MN": ("80%", "State Mandated"),
    "MO": ("80%", "State Mandated"), "MS": ("75%", "State Mandated"),
    "MT": ("80%", "Internal"), "NC": ("75%", "State Mandated"),
    "ND": ("75%", "State Mandated"), "NE": ("75%", "State Mandated"),
    "NH": ("75%", "Mandated — See Below"), "NJ": ("80%", "Internal"),
    "NM": ("80%", "Internal"), "NV": ("65%", "State Mandated — Excludes Paint"),
    "NY": ("75%", "Mandated — 8 years or newer"), "OH": ("75%", "Internal"),
    "OK": ("60%", "State Mandated"), "OR": ("80%", "Internal"),
    "PA": ("80%", "Internal"), "RI": ("75%", "State Mandated"),
    "SC": ("75%", "State Mandated"), "SD": ("80%", "Internal"),
    "TN": ("75%", "State Mandated"), "TX": ("80%", "Internal"),
    "UT": ("Est + Salvage > ACV", "State Mandated"), "VA": ("75%", "State Mandated"),
    "VT": ("80%", "Internal"), "WA": ("80%", "Internal"),
    "WI": ("70%", "State Mandated — 7 years or newer"), "WV": ("75%", "State Mandated"),
    "WY": ("75%", "State Mandated"),
}

STATE_TAX_RULES = {
    "AK": "Tax Everything when Tax Rate applies", "AL": "Parts Only",
    "AR": "Tax Everything", "AZ": "Parts and Materials",
    "CA": "Parts and Materials", "CO": "Parts and Materials",
    "CT": "Parts, All Labor, Materials, Sublet and Betterment",
    "DC": "Parts, All Labor, Materials and Sublet",
    "DE": "No Taxes", "FL": "Parts, All Labor, Materials, Sublet and Betterment",
    "GA": "Parts and Materials", "HI": "Tax Everything",
    "IA": "Tax Everything", "ID": "Parts and Materials",
    "IL": "Parts and Materials", "IN": "Parts and Materials",
    "KS": "Parts, All Labor, Materials, Sublet, Storage and Betterment",
    "KY": "Parts, Material, All Labor and Sublet",
    "LA": "Parts, All Labor, Materials, Sublet and Betterment",
    "MA": "Parts and Materials", "MD": "Parts, Materials and Betterment",
    "ME": "Parts and Materials", "MI": "Parts and Materials",
    "MN": "Parts and Materials", "MO": "Parts and Materials",
    "MS": "Tax Everything", "MT": "No Taxes",
    "NC": "Parts, All Labor, Sublet and Materials",
    "ND": "Parts and Materials", "NE": "Parts, Refinish Labor only and Materials",
    "NH": "No Taxes", "NJ": "Parts, All Labor, Materials, Sublet and Betterment",
    "NM": "Parts, All Labor, Materials, Sublet and Betterment",
    "NV": "Parts and Materials", "NY": "Parts, All Labor, Materials and Sublet",
    "OH": "Parts, All Labor, Materials and Sublet", "OK": "Parts and Materials",
    "OR": "No Taxes", "PA": "Parts, All Labor, Materials and Sublet",
    "RI": "Parts and Materials", "SC": "Parts Only",
    "SD": "Parts, All Labor, Materials, Towing (including Admin fee), Storage",
    "TN": "Tax Everything", "TX": "Parts, Materials and Storage",
    "UT": "Parts, All Labor, Materials, Sublet, Towing and Storage",
    "VA": "Parts, Materials and Sublet", "VT": "Parts and Materials",
    "WA": "Tax Everything", "WI": "Parts, All Labor, Materials, Towing, Sublet and Betterment",
    "WV": "Parts, All Labor, Materials and Sublet", "WY": "Tax Everything",
}

NO_TAX_STATES = {"DE", "MT", "NH", "OR"}
TAX_EVERYTHING_STATES = {"AK", "AR", "HI", "IA", "MS", "TN", "WA", "WY"}
_LICENSE_STATES = {"NY", "CT", "PA", "SC", "NC", "MA", "RI", "DE", "VT"}


# ---------------------------------------------------------------------------
# Rules
# ---------------------------------------------------------------------------

class LicenseNumberRequiredRule(BaseRule):
    """STATE_001: Certain states require license/registration number on all estimates."""
    rule_id = "STATE_001"
    category = "documentation_readiness"
    description = "License/registration number required — verify on estimate"
    severity = "high"

    def applies(self, ctx: AuditContext) -> bool:
        state = (ctx.shop_state() or "").upper()
        return state in _LICENSE_STATES

    def evaluate(self, ctx: AuditContext) -> list[RuleResult]:
        state = (ctx.shop_state() or "").upper()
        shop_name = ctx.metadata.get("shop_name", "Unknown")
        return [RuleResult(
            rule_id=self.rule_id,
            category=self.category,
            severity=self.severity,
            description=f"Shop in {state} — verify license/registration number is on the estimate.",
            line_numbers=[],
            summary=f"State {state} requires license or registration number on all estimates. Shop: {shop_name}.",
            detail=f"State {state} requires license or registration number on all estimates. Shop: {shop_name}.",
            action=f"Confirm license/registration number is on estimate for {state}.",
        )]


class StateTaxVerificationRule(BaseRule):
    """STATE_002: Verify CCC Rates tab matches state tax requirements."""
    rule_id = "STATE_002"
    category = "carrier_compliance"
    description = "Incorrect tax configuration is a frequent carrier revision trigger"
    severity = "high"

    def applies(self, ctx: AuditContext) -> bool:
        return bool(ctx.shop_state())

    def evaluate(self, ctx: AuditContext) -> list[RuleResult]:
        state = (ctx.shop_state() or "").upper()
        zip_code = ctx.shop_zip() or ""
        tax_rule = STATE_TAX_RULES.get(state, "Unknown — verify manually")

        if state in NO_TAX_STATES:
            summary = f"State {state} has NO taxes — verify tax is NOT applied on estimate."
            detail = f"State {state} does not collect sales tax on auto repairs. Verify Rates tab has NO tax categories checked."
            sev = "critical"
        elif state in TAX_EVERYTHING_STATES:
            summary = f"State {state} taxes everything — verify all categories checked."
            detail = f"State {state} requires tax on ALL categories. Verify Rates tab has Parts, Labor, Materials, Sublet all checked."
            sev = "high"
        else:
            if zip_code:
                summary = f"State {state}, ZIP {zip_code}: {tax_rule} — verify Rates tab matches."
                detail = f"ZIP {zip_code} in state {state} may have local tax rules. Verify CCC Rates tab: {tax_rule}."
            else:
                summary = f"State {state}: {tax_rule} — verify Rates tab matches."
                detail = f"State {state} tax requirement: {tax_rule}. Verify Rates tab before locking."
            sev = "high"

        return [RuleResult(
            rule_id=self.rule_id,
            category=self.category,
            severity=sev,
            description=summary,
            line_numbers=[],
            summary=summary,
            detail=detail,
            action=(
                f"Open CCC Rates tab. Verify tax configuration matches {state} requirements: "
                f"{tax_rule}. Confirm tax rate by ZIP code before locking."
            ),
        )]


class TotalLossThresholdRule(BaseRule):
    """STATE_003: Alerts auditor to state-specific total loss threshold."""
    rule_id = "STATE_003"
    category = "carrier_compliance"
    description = "State-specific total loss threshold — critical for borderline files"
    severity = "high"

    def applies(self, ctx: AuditContext) -> bool:
        return bool(ctx.shop_state())

    def evaluate(self, ctx: AuditContext) -> list[RuleResult]:
        state = (ctx.shop_state() or "").upper()
        threshold, mandate = STATE_TL_THRESHOLDS.get(state, ("Unknown", "Unknown"))

        if threshold is None:
            summary = f"State {state} has NO total loss threshold mandate."
            detail = f"State {state} does not have a statutory total loss threshold. Use carrier guidelines."
            sev = "medium"
        else:
            is_mandated = "State Mandated" in mandate
            sev = "critical" if is_mandated else "high"
            summary = f"State {state} TL threshold: {threshold} ({mandate})."
            detail = (
                f"State {state} total loss threshold: {threshold}. Type: {mandate}. "
                + ("This is a STATE MANDATE — must be followed by law." if is_mandated else "This is an internal carrier guideline.")
            )

        return [RuleResult(
            rule_id=self.rule_id,
            category=self.category,
            severity=sev,
            description=summary,
            line_numbers=[],
            summary=summary,
            detail=detail,
            action=(
                f"Verify estimate total against {state} threshold of "
                f"{threshold or 'carrier guidelines'}. "
                f"If approaching threshold, use NADA Clean Retail and escalate if borderline."
            ),
        )]
