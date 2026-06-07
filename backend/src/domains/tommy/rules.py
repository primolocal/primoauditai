"""
Tommy's Audit Brain — rules extracted from the audit reference document.
Cover car, total loss threshold, dealer invoice, frame setup, alignment,
damage-to-value check, hail windshield causation, and escalation triggers.
"""

from src.engine.base import BaseRule, RuleResult
from src.engine.context import AuditContext


class CoverCarRequiredRule(BaseRule):
    """
    PAINT_001: Cover Car — Required with Refinish.
    """
    rule_id = "PAINT_001"
    category = "line_item_support"
    description = "Cover car is missing from estimate that has refinish operations"
    severity = "high"

    def applies(self, ctx: AuditContext) -> bool:
        return True

    def evaluate(self, ctx: AuditContext) -> list[RuleResult]:
        has_refinish = any(
            str(line.get("operation_label", "")).lower() == "refinish"
            for line in ctx.get_all_lines()
        )
        has_cover = any(
            "cover car" in str(line.get("description", "")).lower()
            for line in ctx.get_all_lines()
        )
        if has_refinish and not has_cover:
            return [RuleResult(
                rule_id=self.rule_id,
                category=self.category,
                severity=self.severity,
                description=self.description,
                summary="Refinish on estimate — cover car is missing.",
                detail="Cover car warranted anytime vehicle goes into paint booth. Missing = return trigger.",
                action="Add cover car to the estimate.",
            )]
        return []


class TotalLossThresholdFlagRule(BaseRule):
    """
    TL_001: Total Loss Threshold — Review.
    Verify total loss threshold when estimate exceeds $5,000.
    """
    rule_id = "TL_001"
    category = "carrier_compliance"
    description = "Estimate exceeds total loss threshold — NADA required"
    severity = "high"

    def applies(self, ctx: AuditContext) -> bool:
        return True

    def evaluate(self, ctx: AuditContext) -> list[RuleResult]:
        total = ctx.total_estimate()
        if total > 5000:
            sev = "critical" if total > 10000 else self.severity
            return [RuleResult(
                rule_id=self.rule_id,
                category=self.category,
                severity=sev,
                description=self.description,
                summary=f"Estimate ${total:,.0f} — verify total loss threshold. NADA required.",
                detail=f"${total:,.0f} estimate. Route to carrier if nearing 60% of NADA value.",
                action="Attach NADA Clean Retail. Escalate if near threshold.",
            )]
        return []


class LumpSumDealerInvoiceRule(BaseRule):
    """
    SUPP_008: Dealer Invoice — Itemize Per Operation.
    NatGen: lump-sum dealer invoices not approved. Each op = individual CCC labor line.
    """
    rule_id = "SUPP_008"
    category = "documentation_readiness"
    description = "Dealer invoice must be itemized per operation, not lump-sum"
    severity = "high"

    def applies(self, ctx: AuditContext) -> bool:
        return True

    def evaluate(self, ctx: AuditContext) -> list[RuleResult]:
        results = []
        for line in ctx.get_all_lines():
            if line.get("is_header"):
                continue
            supp = str(line.get("supplement", ""))
            if not supp or supp == "E01":
                continue
            desc = str(line.get("description", "")).lower()
            if "dealer" in desc or "invoice" in desc:
                results.append(RuleResult(
                    rule_id=self.rule_id,
                    category=self.category,
                    severity=self.severity,
                    description=self.description,
                    line_numbers=[line.get("line_no")],
                    summary=f"Dealer invoice L{line.get('line_no')} — verify itemized per operation.",
                    detail="NatGen: lump-sum dealer invoices not approved. Each op = individual CCC labor line.",
                    action="Itemize dealer invoice per operation.",
                ))
        return results


class FrameSetupMeasureRule(BaseRule):
    """
    FRAME_001: Frame Damage — Set-up & Measure Required.
    Set-up and measure must be on estimate when frame damage present.
    """
    rule_id = "FRAME_001"
    category = "line_item_support"
    description = "Frame damage detected but set-up and measure is missing"
    severity = "high"

    def applies(self, ctx: AuditContext) -> bool:
        return True

    def evaluate(self, ctx: AuditContext) -> list[RuleResult]:
        has_frame = any(
            "frame" in str(line.get("description", "")).lower()
            or line.get("financial_signature", {}).get("labor_amount_frame", 0) > 0
            for line in ctx.get_all_lines()
        )
        has_setup = any(
            "set" in str(line.get("description", "")).lower()
            and "measur" in str(line.get("description", "")).lower()
            for line in ctx.get_all_lines()
        )
        if has_frame and not has_setup:
            return [RuleResult(
                rule_id=self.rule_id,
                category=self.category,
                severity=self.severity,
                description=self.description,
                summary="Frame damage detected — set-up and measure is missing.",
                detail="Set-up and measure must be on estimate when frame damage present. Most commonly missed frame line.",
                action="Add set-up and measure for frame damage.",
            )]
        return []


class AlignmentRequiredRule(BaseRule):
    """
    ALIGN_001: Tire/Wheel Damage — Alignment Required.
    Any tire/wheel damage warrants alignment. Skipped on hail claims.
    """
    rule_id = "ALIGN_001"
    category = "line_item_support"
    description = "Tire/wheel damage detected but alignment may be warranted"
    severity = "high"

    def applies(self, ctx: AuditContext) -> bool:
        return not ctx.is_hail_claim()

    def evaluate(self, ctx: AuditContext) -> list[RuleResult]:
        tire_keywords = ("tire", "wheel", "rim")
        has_tire = any(
            any(kw in str(line.get("description", "")).lower() for kw in tire_keywords)
            for line in ctx.get_all_lines()
        )
        has_align = any(
            "align" in str(line.get("description", "")).lower()
            for line in ctx.get_all_lines()
        )
        if has_tire and not has_align:
            return [RuleResult(
                rule_id=self.rule_id,
                category=self.category,
                severity=self.severity,
                description=self.description,
                summary="Tire/wheel damage detected — alignment may be warranted.",
                detail="Any tire/wheel damage warrants alignment. Impact shifts geometry regardless of visible suspension damage.",
                action="Review for wheel alignment. Add if tire/wheel damage confirmed.",
            )]
        return []


class DamageToValueCheckRule(BaseRule):
    """
    CHECK_006: Damage-to-Value % — Required in Notes.
    AE-197, AE-215: estimate notes must include percent damage to value on ALL estimates. No exceptions.
    """
    rule_id = "CHECK_006"
    category = "documentation_readiness"
    description = "Damage-to-value percentage must be in estimate notes"
    severity = "high"

    def applies(self, ctx: AuditContext) -> bool:
        return True

    def evaluate(self, ctx: AuditContext) -> list[RuleResult]:
        total = ctx.total_estimate()
        if total > 3000:
            return [RuleResult(
                rule_id=self.rule_id,
                category=self.category,
                severity=self.severity,
                description=self.description,
                summary=f"Estimate ${total:,.0f} — damage-to-value percentage must be in estimate notes. NO EXCEPTIONS.",
                detail="NatGen/IAnet: estimate notes must include percent of damage to value on ALL estimates. This includes all original and supplement estimates.",
                action="Add damage-to-value percentage in estimate notes.",
            )]
        return []


class HailWindshieldCausationRule(BaseRule):
    """
    HAIL_002: Hail — Windshield Causation Required.
    CK-058: Windshield replacement on hail only when hail directly caused break. Rock chips don't qualify.
    """
    rule_id = "HAIL_002"
    category = "line_item_support"
    description = "Windshield replacement on hail claim — verify hail directly caused break"
    severity = "high"

    def applies(self, ctx: AuditContext) -> bool:
        return ctx.is_hail_claim()

    def evaluate(self, ctx: AuditContext) -> list[RuleResult]:
        results = []
        for line in ctx.get_all_lines():
            if line.get("is_header"):
                continue
            desc = str(line.get("description", "")).lower()
            if "windshield" not in desc and "glass" not in desc:
                continue
            if "repl" not in desc and "replace" not in desc:
                continue
            results.append(RuleResult(
                rule_id=self.rule_id,
                category=self.category,
                severity=self.severity,
                description=self.description,
                line_numbers=[line.get("line_no")],
                summary=f"Windshield replacement on hail claim L{line.get('line_no')} — verify hail directly caused break.",
                detail="NatGen: windshield replacement on hail claims is supported ONLY when hail directly caused the break. Rock chips do not qualify.",
                action="Verify windshield break in hail photos. If rock chip, remove or document as unrelated.",
            ))
        return results


class EscalationTriggerRule(BaseRule):
    """
    ESCALATE_001: Multiple high-severity findings or >$10K suggest escalation.
    AE-008: One back-and-forth then escalate — don't waste rounds.
    """
    rule_id = "ESCALATE_001"
    category = "documentation_readiness"
    description = "Estimate exceeds $10K — consider escalation to manager"
    severity = "medium"

    def applies(self, ctx: AuditContext) -> bool:
        return True

    def evaluate(self, ctx: AuditContext) -> list[RuleResult]:
        total = ctx.total_estimate()
        if total > 10000:
            sev = "high" if total > 15000 else self.severity
            return [RuleResult(
                rule_id=self.rule_id,
                category=self.category,
                severity=sev,
                description=self.description,
                summary=f"${total:,.0f} estimate — consider escalation per Tommy's audit brain (AE-008).",
                detail="If unsure which guideline applies or if findings are complex, contact Rachael or Tommy before proceeding. One back-and-forth then escalate.",
                action="Review findings. If uncertain, escalate to manager.",
            )]
        return []
