"""
Tommy's Audit Brain — rules extracted from the audit reference document.
Cover car, total loss threshold, dealer invoice, frame setup, alignment.
Also includes Damage-to-value check, hail windshield causation, and escalation triggers
(merged from audit_brain_rules.py).
"""
from typing import List
from audit_context import AuditContext
from rules.base import BaseRule, RuleResult


class CoverCarRequiredRule(BaseRule):
    rule_id = "PAINT_001"
    title = "Cover Car — Required with Refinish"
    category = "line_item_support"
    severity = "high"
    def applies(self, ctx): return True
    def evaluate(self, ctx):
        results = []
        has_refinish = any(str(r.get("operation_label","")).lower() == "refinish" for r in ctx.get_all_lines())
        has_cover = any("cover car" in str(r.get("description","")).lower() for r in ctx.get_all_lines())
        if has_refinish and not has_cover:
            results.append(RuleResult(rule_id=self.rule_id, title=self.title, category=self.category,
                severity=self.severity, affected_lines=[],
                summary="Refinish on estimate — cover car is missing.",
                why_flagged="Cover car warranted anytime vehicle goes into paint booth. Missing = return trigger.",
                recommended_actions="Add cover car to the estimate.", status="unreviewed"))
        return results


class TotalLossThresholdFlagRule(BaseRule):
    rule_id = "TL_001"
    title = "Total Loss Threshold — Review"
    category = "carrier_compliance"
    severity = "high"
    def applies(self, ctx): return True
    def evaluate(self, ctx):
        results = []
        total = ctx.total_estimate()
        if total > 5000:
            results.append(RuleResult(rule_id=self.rule_id, title=self.title, category=self.category,
                severity="critical" if total>10000 else "high", affected_lines=[],
                summary=f"Estimate ${total:,.0f} — verify total loss threshold. NADA required.",
                why_flagged=f"${total:,.0f} estimate. Route to carrier if nearing 60% of NADA value.",
                recommended_actions="Attach NADA Clean Retail. Escalate if near threshold.", status="unreviewed"))
        return results


class LumpSumDealerInvoiceRule(BaseRule):
    rule_id = "SUPP_008"
    title = "Dealer Invoice — Itemize Per Operation"
    category = "documentation_readiness"
    severity = "high"
    def applies(self, ctx): return True
    def evaluate(self, ctx):
        results = []
        for line in ctx.get_all_lines():
            if line.get("is_header"): continue
            supp = str(line.get("supplement",""))
            if not supp or supp=="E01": continue
            desc = str(line.get("description","")).lower()
            if "dealer" in desc or "invoice" in desc:
                results.append(RuleResult(rule_id=self.rule_id, title=self.title, category=self.category,
                    severity=self.severity, affected_lines=[line.get("line_no")],
                    summary=f"Dealer invoice L{line.get('line_no')} — verify itemized per operation.",
                    why_flagged="NatGen: lump-sum dealer invoices not approved. Each op = individual CCC labor line.",
                    recommended_actions="Itemize dealer invoice per operation.", status="unreviewed"))
        return results


class FrameSetupMeasureRule(BaseRule):
    rule_id = "FRAME_001"
    title = "Frame Damage — Set-up & Measure Required"
    category = "line_item_support"
    severity = "high"
    def applies(self, ctx): return True
    def evaluate(self, ctx):
        results = []
        has_frame = any("frame" in str(r.get("description","")).lower() or r.get("financial_signature",{}).get("labor_amount_frame",0)>0 for r in ctx.get_all_lines())
        has_setup = any("set" in str(r.get("description","")).lower() and "measur" in str(r.get("description","")).lower() for r in ctx.get_all_lines())
        if has_frame and not has_setup:
            results.append(RuleResult(rule_id=self.rule_id, title=self.title, category=self.category,
                severity=self.severity, affected_lines=[],
                summary="Frame damage detected — set-up and measure is missing.",
                why_flagged="Set-up and measure must be on estimate when frame damage present. Most commonly missed frame line.",
                recommended_actions="Add set-up and measure for frame damage.", status="unreviewed"))
        return results


class AlignmentRequiredRule(BaseRule):
    rule_id = "ALIGN_001"
    title = "Tire/Wheel Damage — Alignment Required"
    category = "line_item_support"
    severity = "high"
    def applies(self, ctx): return True
    def evaluate(self, ctx):
        results = []
        # Skip hail claims — tire/wheel mentions are R&I for access, not collision damage
        if ctx.is_hail_claim():
            return results

        has_tire = any(any(kw in str(r.get("description","")).lower() for kw in ("tire","wheel","rim")) for r in ctx.get_all_lines())
        has_align = any("align" in str(r.get("description","")).lower() for r in ctx.get_all_lines())
        if has_tire and not has_align:
            results.append(RuleResult(rule_id=self.rule_id, title=self.title, category=self.category,
                severity=self.severity, affected_lines=[],
                summary="Tire/wheel damage detected — alignment may be warranted.",
                why_flagged="Any tire/wheel damage warrants alignment. Impact shifts geometry regardless of visible suspension damage.",
                recommended_actions="Review for wheel alignment. Add if tire/wheel damage confirmed.", status="unreviewed"))
        return results


# ============================================================================
# Additional QC checks — merged from audit_brain_rules.py
# ============================================================================


class DamageToValueCheckRule(BaseRule):
    """CHECK_006: Percent damage to value must be in estimate notes. AE-197, AE-215."""
    rule_id = "CHECK_006"
    title = "Damage-to-Value % — Required in Notes"
    category = "documentation_readiness"
    severity = "high"

    def applies(self, ctx): return True

    def evaluate(self, ctx):
        results = []
        total = ctx.total_estimate()
        if total > 3000:
            results.append(RuleResult(
                rule_id=self.rule_id, title=self.title, category=self.category,
                severity=self.severity, affected_lines=[],
                summary=f"Estimate ${total:,.0f} — damage-to-value percentage must be in estimate notes. NO EXCEPTIONS.",
                why_flagged=(
                    "NatGen/IAnet: estimate notes must include percent of damage to value on ALL estimates. "
                    "No exceptions. This includes all original and supplement estimates."
                ),
                recommended_actions="Add damage-to-value percentage in estimate notes.",
                status="unreviewed",
            ))
        return results


class HailWindshieldCausationRule(BaseRule):
    """CK-058: Windshield replacement on hail only when hail directly caused break. Rock chips don't qualify."""
    rule_id = "HAIL_002"
    title = "Hail — Windshield Causation Required"
    category = "line_item_support"
    severity = "high"

    def applies(self, ctx): return True

    def evaluate(self, ctx):
        results = []
        if not ctx.is_hail_claim():
            return results

        for line in ctx.get_all_lines():
            if line.get("is_header"): continue
            desc = str(line.get("description", "")).lower()
            if "windshield" not in desc and "glass" not in desc:
                continue
            if "repl" not in desc and "replace" not in desc:
                continue

            results.append(RuleResult(
                rule_id=self.rule_id, title=self.title, category=self.category,
                severity=self.severity, affected_lines=[line.get("line_no")],
                summary=f"Windshield replacement on hail claim L{line.get('line_no')} — verify hail directly caused break.",
                why_flagged=(
                    "NatGen: windshield replacement on hail claims is supported ONLY when hail "
                    "directly caused the break. Rock chips do not qualify. Verify causation in photos."
                ),
                recommended_actions="Verify windshield break in hail photos. If rock chip, remove or document as unrelated.",
                status="unreviewed",
            ))
        return results


class EscalationTriggerRule(BaseRule):
    """ESCALATE_001: Multiple high-severity findings or >$10K suggest escalation. AE-008."""
    rule_id = "ESCALATE_001"
    title = "Escalation Suggested — Multiple High Findings"
    category = "documentation_readiness"
    severity = "medium"

    def applies(self, ctx): return True

    def evaluate(self, ctx):
        results = []
        total = ctx.total_estimate()
        if total > 10000:
            results.append(RuleResult(
                rule_id=self.rule_id, title=self.title, category=self.category,
                severity="medium" if total < 15000 else "high", affected_lines=[],
                summary=f"${total:,.0f} estimate — consider escalation per Tommy's audit brain (AE-008).",
                why_flagged=(
                    "If unsure which guideline applies or if findings are complex, "
                    "contact Rachael or Tommy before proceeding. One back-and-forth then escalate."
                ),
                recommended_actions="Review findings. If uncertain, escalate to manager.",
                status="unreviewed",
            ))
        return results
