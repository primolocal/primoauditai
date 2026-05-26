"""
State-specific rules — triggers based on shop/inspection location state.
Covers license/registration requirements and tax configuration.
"""
from typing import List
from audit_context import AuditContext
from rules.base import BaseRule, RuleResult


class LicenseNumberRequiredRule(BaseRule):
    """
    STATE_001: Certain states require license/registration number on all estimates.
    If shop is in NY, CT, PA, SC, NC, MA, RI, DE, VT — warn auditor to verify.
    """
    rule_id = "STATE_001"
    title = "License Number Required — Verify"
    category = "documentation_readiness"
    severity = "high"
    _LICENSE_STATES = {"NY", "CT", "PA", "SC", "NC", "MA", "RI", "DE", "VT"}

    def applies(self, ctx: AuditContext) -> bool:
        shop = ctx.raw_data.get("claim_meta", {}).get("shop", {})
        state = (shop.get("state", "") or "").upper()
        return state in self._LICENSE_STATES

    def evaluate(self, ctx: AuditContext) -> List[RuleResult]:
        shop = ctx.raw_data.get("claim_meta", {}).get("shop", {})
        state = (shop.get("state", "") or "").upper()
        return [RuleResult(
            rule_id=self.rule_id, title=self.title, category=self.category,
            severity=self.severity, affected_lines=[],
            summary=f"Shop in {state} — verify license/registration number is on the estimate.",
            why_flagged=(
                f"State {state} requires license or registration number on all estimates. "
                f"Shop: {shop.get('name', 'Unknown')}. "
            ),
            recommended_actions=f"Confirm license/registration number is on estimate for {state}.",
            status="unreviewed",
        )]


# ============================================================================
# State Tax Rules
# ============================================================================


# State tax requirements — what to tax in each state
STATE_TL_THRESHOLDS = {
    "AK": ("80%", "Internal"),
    "AL": ("75%", "State Mandated"),
    "AR": ("70%", "State Mandated"),
    "AZ": ("80%", "Internal"),
    "CA": (None, "No State Mandate"),
    "CO": ("80%", "Internal"),
    "CT": (None, "No State Mandate"),
    "DC": ("75%", "State Mandated"),
    "DE": ("80%", "State Mandated"),
    "FL": ("80%", "State Mandated"),
    "GA": ("80%", "Internal"),
    "HI": ("75%", "Internal"),
    "IA": ("80%", "Internal"),
    "ID": ("80%", "Internal"),
    "IL": ("80%", "Internal"),
    "IN": ("80%", "Internal"),
    "KS": ("75%", "State Mandated"),
    "KY": ("75%", "State Mandated"),
    "LA": ("75%", "State Mandated"),
    "MA": (None, "No State Mandate"),
    "MD": ("75%", "State Mandated"),
    "ME": ("80%", "Internal"),
    "MI": ("75%", "State Mandated"),
    "MN": ("80%", "State Mandated"),
    "MO": ("80%", "State Mandated"),
    "MS": ("75%", "State Mandated"),
    "MT": ("80%", "Internal"),
    "NC": ("75%", "State Mandated"),
    "ND": ("75%", "State Mandated"),
    "NE": ("75%", "State Mandated"),
    "NH": ("75%", "Mandated — See Below"),
    "NJ": ("80%", "Internal"),
    "NM": ("80%", "Internal"),
    "NV": ("65%", "State Mandated — Excludes Paint"),
    "NY": ("75%", "Mandated — 8 years or newer"),
    "OH": ("75%", "Internal"),
    "OK": ("60%", "State Mandated"),
    "OR": ("80%", "Internal"),
    "PA": ("80%", "Internal"),
    "RI": ("75%", "State Mandated"),
    "SC": ("75%", "State Mandated"),
    "SD": ("80%", "Internal"),
    "TN": ("75%", "State Mandated"),
    "TX": ("80%", "Internal"),
    "UT": ("Est + Salvage > ACV", "State Mandated"),
    "VA": ("75%", "State Mandated"),
    "VT": ("80%", "Internal"),
    "WA": ("80%", "Internal"),
    "WI": ("70%", "State Mandated — 7 years or newer"),
    "WV": ("75%", "State Mandated"),
    "WY": ("75%", "State Mandated"),
}

STATE_TAX_RULES = {
    "AK": "Tax Everything when Tax Rate applies",
    "AL": "Parts Only",
    "AR": "Tax Everything",
    "AZ": "Parts and Materials",
    "CA": "Parts and Materials",
    "CO": "Parts and Materials",
    "CT": "Parts, All Labor, Materials, Sublet and Betterment",
    "DC": "Parts, All Labor, Materials and Sublet",
    "DE": "No Taxes",
    "FL": "Parts, All Labor, Materials, Sublet and Betterment",
    "GA": "Parts and Materials",
    "HI": "Tax Everything",
    "IA": "Tax Everything",
    "ID": "Parts and Materials",
    "IL": "Parts and Materials",
    "IN": "Parts and Materials",
    "KS": "Parts, All Labor, Materials, Sublet, Storage and Betterment",
    "KY": "Parts, Material, All Labor and Sublet",
    "LA": "Parts, All Labor, Materials, Sublet and Betterment",
    "MA": "Parts and Materials",
    "MD": "Parts, Materials and Betterment",
    "ME": "Parts and Materials",
    "MI": "Parts and Materials",
    "MN": "Parts and Materials",
    "MO": "Parts and Materials",
    "MS": "Tax Everything",
    "MT": "No Taxes",
    "NC": "Parts, All Labor, Sublet and Materials",
    "ND": "Parts and Materials",
    "NE": "Parts, Refinish Labor only and Materials",
    "NH": "No Taxes",
    "NJ": "Parts, All Labor, Materials, Sublet and Betterment",
    "NM": "Parts, All Labor, Materials, Sublet and Betterment",
    "NV": "Parts and Materials",
    "NY": "Parts, All Labor, Materials and Sublet",
    "OH": "Parts, All Labor, Materials and Sublet",
    "OK": "Parts and Materials",
    "OR": "No Taxes",
    "PA": "Parts, All Labor, Materials and Sublet",
    "RI": "Parts and Materials",
    "SC": "Parts Only",
    "SD": "Parts, All Labor, Materials, Towing (including Admin fee), Storage",
    "TN": "Tax Everything",
    "TX": "Parts, Materials and Storage",
    "UT": "Parts, All Labor, Materials, Sublet, Towing and Storage",
    "VA": "Parts, Materials and Sublet",
    "VT": "Parts and Materials",
    "WA": "Tax Everything",
    "WI": "Parts, All Labor, Materials, Towing, Sublet and Betterment",
    "WV": "Parts, All Labor, Materials and Sublet",
    "WY": "Tax Everything",
}

# States with no tax — no verification needed beyond confirming zero tax
NO_TAX_STATES = {"DE", "MT", "NH", "OR"}

# States that tax everything — auditor should verify all categories are checked
TAX_EVERYTHING_STATES = {"AK", "AR", "HI", "IA", "MS", "TN", "WA", "WY"}


class StateTaxVerificationRule(BaseRule):
    """
    STATE_002: Verify CCC Rates tab matches state tax requirements.
    Incorrect tax configuration is a frequent carrier revision trigger.
    """
    rule_id = "STATE_002"
    title = "State Tax Configuration — Verify"
    category = "carrier_compliance"
    severity = "high"

    def applies(self, ctx: AuditContext) -> bool:
        shop = ctx.raw_data.get("claim_meta", {}).get("shop", {})
        state = (shop.get("state", "") or "").upper()
        return bool(state)

    def evaluate(self, ctx: AuditContext) -> List[RuleResult]:
        shop = ctx.raw_data.get("claim_meta", {}).get("shop", {})
        state = (shop.get("state", "") or "").upper()
        tax_rule = STATE_TAX_RULES.get(state, "Unknown — verify manually")

        if state in NO_TAX_STATES:
            summary = f"State {state} has NO taxes — verify tax is NOT applied on estimate."
            why = (
                f"State {state} does not collect sales tax on auto repairs. "
                f"Verify the Rates tab in CCC has NO tax categories checked. "
                f"Applying tax in a no-tax state will cause a revision."
            )
            severity = "critical"
        elif state in TAX_EVERYTHING_STATES:
            summary = f"State {state} taxes everything — verify all categories checked."
            why = (
                f"State {state} requires tax on ALL categories. "
                f"Verify the Rates tab has Parts, Labor, Materials, Sublet all checked. "
                f"Missing tax categories will cause a revision."
            )
            severity = "high"
        else:
            summary = f"State {state}: {tax_rule} — verify Rates tab matches."
            why = (
                f"State {state} tax requirement: {tax_rule}. "
                f"Verify the CCC Rates tab is configured correctly before locking the estimate. "
                f"Incorrect tax configuration is a frequent carrier revision trigger."
            )
            severity = "high"

        return [RuleResult(
            rule_id=self.rule_id,
            title=self.title,
            category=self.category,
            severity=severity,
            affected_lines=[],
            summary=summary,
            why_flagged=why,
            recommended_actions=(
                f"Open CCC Rates tab. Verify tax configuration matches {state} requirements: "
                f"{tax_rule}. Check the box to apply state taxes to correct categories. "
                f"Confirm tax rate by ZIP code before locking."
            ),
            status="unreviewed",
        )]


class TotalLossThresholdRule(BaseRule):
    """
    STATE_003: Alerts auditor to state-specific total loss threshold.
    Critical for borderline files — using wrong threshold triggers revisions.
    """
    rule_id = "STATE_003"
    title = "Total Loss Threshold — State Specific"
    category = "carrier_compliance"
    severity = "high"

    def applies(self, ctx: AuditContext) -> bool:
        shop = ctx.raw_data.get("claim_meta", {}).get("shop", {})
        state = (shop.get("state", "") or "").upper()
        return bool(state)

    def evaluate(self, ctx: AuditContext) -> List[RuleResult]:
        shop = ctx.raw_data.get("claim_meta", {}).get("shop", {})
        state = (shop.get("state", "") or "").upper()
        threshold, mandate = STATE_TL_THRESHOLDS.get(state, ("Unknown", "Unknown"))

        if threshold is None:
            summary = f"State {state} has NO total loss threshold mandate."
            why = (
                f"State {state} does not have a statutory total loss threshold. "
                f"Total loss determination should use carrier guidelines and sound judgment."
            )
            severity = "medium"
        else:
            summary = f"State {state} TL threshold: {threshold} ({mandate})."
            is_mandated = "State Mandated" in mandate
            severity = "critical" if is_mandated else "high"
            why = (
                f"State {state} total loss threshold: {threshold}. "
                f"Type: {mandate}. "
                + ("This is a STATE MANDATE — must be followed by law."
                   if is_mandated else "This is an internal carrier guideline.")
            )

        return [RuleResult(
            rule_id=self.rule_id, title=self.title, category=self.category,
            severity=severity, affected_lines=[],
            summary=summary, why_flagged=why,
            recommended_actions=(
                f"Verify estimate total against {state} threshold of "
                f"{threshold or 'carrier guidelines'}. "
                f"If approaching threshold, use NADA Clean Retail and escalate if borderline."
            ),
            status="unreviewed",
        )]

