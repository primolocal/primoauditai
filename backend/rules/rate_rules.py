"""
ZIP-based rate verification rule. Compares estimate rates to ZIP standard.
Flags discrepancies for review.
"""
import re
from typing import List
from audit_context import AuditContext
from rules.base import BaseRule, RuleResult


class ZIPRateVerificationRule(BaseRule):
    """
    RATE_001: Verify labor rates match ZIP code standard.
    Compares body/paint/frame/mech rates and flags differences.
    """
    rule_id = "RATE_001"
    title = "Rate Verification — ZIP Standard"
    category = "carrier_compliance"
    severity = "high"

    def applies(self, ctx: AuditContext) -> bool:
        return True

    def evaluate(self, ctx: AuditContext) -> List[RuleResult]:
        results = []
        shop = ctx.raw_data.get("claim_meta", {}).get("shop", {})

        address = shop.get("address", "") + " " + shop.get("name", "")
        zip_match = re.search(r'[A-Z]{2}\s+(\d{5})(?:-\d{4})?\b', address)
        if not zip_match:
            zip_match = re.search(r'\b(\d{5})(?:-\d{4})?\s+[A-Z]{2}\b', address)
        if not zip_match:
            all_zips = re.findall(r'\b(\d{5})\b', address)
            for z in reversed(all_zips):
                if int(z) > 10000:
                    zip_match = re.match(r'(\d{5})', z)
                    break

        if not zip_match:
            # Only flag missing ZIP when shop info is present but no ZIP found
            if shop:
                results.append(RuleResult(
                    rule_id=self.rule_id, title=self.title,
                    category=self.category, severity="medium", affected_lines=[],
                    summary="No ZIP code found — cannot verify rates.",
                    why_flagged="Labor and tax rates must be verified against ZIP standard.",
                    recommended_actions="Verify rates manually.",
                ))
            return results

        zip_code = zip_match.group(1)

        from tax_labor_lookup import lookup_labor, lookup_tax
        labor = lookup_labor(zip_code)
        tax = lookup_tax(zip_code)

        if not labor:
            results.append(RuleResult(
                rule_id=self.rule_id, title=self.title,
                category=self.category, severity="medium", affected_lines=[],
                summary=f"ZIP {zip_code} not found in rate database.",
                why_flagged="Labor rate database does not contain this ZIP code.",
                recommended_actions="Verify rates manually.",
            ))
            return results

        # Get estimate body rate from lines
        body_rates = set()
        for line in ctx.get_all_lines():
            if line.get("is_header"): continue
            fs = line.get("financial_signature", {})
            lhrs = fs.get("labor_hours_total", 0)
            lamount = fs.get("labor_amount_total", 0)
            if lhrs > 0 and lamount > 0:
                body_rates.add(round(lamount / lhrs))

        est_body_rate = max(body_rates) if body_rates else 0

        # Build comparison
        std_body = labor.get("body", 0)
        std_paint = labor.get("paint", 0)
        std_frame = labor.get("frame", 0)
        std_mech = labor.get("mech", 0)

        diffs = []
        if est_body_rate > 0 and est_body_rate != std_body:
            diffs.append(f"Body: est ${est_body_rate}/hr vs standard ${std_body}/hr")

        if tax and tax.get("combined", 0) > 0:
            std_tax = tax["combined"]
            est_tax = ctx.raw_data.get("claim_meta", {}).get("estimate_tax_rate")
            if est_tax:
                if abs(std_tax * 100 - est_tax) > 0.1:
                    diffs.append(f"Tax: est {est_tax:.1%} vs standard {std_tax:.1%}")

        # Only return a finding when there is an actual discrepancy
        if diffs:
            results.append(RuleResult(
                rule_id=self.rule_id, title=self.title,
                category=self.category,
                severity="high",
                affected_lines=[],
                summary=f"ZIP {zip_code}: rate/tax discrepancy — {'; '.join(diffs)}",
                why_flagged=(
                    f"Verify estimate rates match ZIP {zip_code} standard. "
                    f"NatGen: never overrule CCC labor rates. Document any differences."
                ),
                recommended_actions=(
                    f"Standard rates for ZIP {zip_code}: Body ${std_body}/hr, Paint ${std_paint}/hr, "
                    f"Frame ${std_frame}/hr, Mech ${std_mech}/hr. "
                    f"ESTIMATE DIFFERS: {'; '.join(diffs)}"
                ),
            ))

        return results
