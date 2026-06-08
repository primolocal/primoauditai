"""ZIP-based rate verification rule. Compares estimate rates to ZIP standard.
"""
from __future__ import annotations

import re

from src.engine.base import BaseRule, RuleResult
from src.engine.context import AuditContext


# Stub rate lookups — wire to actual database or JSON in production
def lookup_labor(zip_code: str) -> dict | None:
    """Return standard labor rates for ZIP code. Stub: returns None."""
    return None


def lookup_tax(zip_code: str) -> dict | None:
    """Return standard tax rate for ZIP code. Stub: returns None."""
    return None


class ZIPRateVerificationRule(BaseRule):
    """RATE_001: Verify labor rates match ZIP code standard."""
    rule_id = "RATE_001"
    category = "carrier_compliance"
    description = "Verify estimate labor rates and tax match ZIP standard"
    severity = "high"

    def applies(self, ctx: AuditContext) -> bool:
        return True

    def evaluate(self, ctx: AuditContext) -> list[RuleResult]:
        results = []
        shop_address = str(ctx.metadata.get("shop_address", ""))
        shop_name = str(ctx.metadata.get("shop_name", ""))
        address = shop_address + " " + shop_name

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
            if shop_address or shop_name:
                results.append(RuleResult(
                    rule_id=self.rule_id,
                    category=self.category,
                    severity="medium",
                    description="No ZIP code found — cannot verify rates.",
                    line_numbers=[],
                    summary="No ZIP code found — cannot verify rates.",
                    detail="Labor and tax rates must be verified against ZIP standard.",
                    action="Verify rates manually.",
                ))
            return results

        zip_code = zip_match.group(1)
        labor = lookup_labor(zip_code)
        tax = lookup_tax(zip_code)

        if not labor:
            results.append(RuleResult(
                rule_id=self.rule_id,
                category=self.category,
                severity="medium",
                description=f"ZIP {zip_code} not found in rate database.",
                line_numbers=[],
                summary=f"ZIP {zip_code} not found in rate database.",
                detail="Labor rate database does not contain this ZIP code.",
                action="Verify rates manually.",
            ))
            return results

        # Get estimate body rate from lines
        body_rates = set()
        for line in ctx.get_all_lines():
            if line.get("is_header"):
                continue
            fs = line.get("financial_signature", {})
            lhrs = fs.get("labor_hours_total", 0)
            lamount = fs.get("labor_amount_total", 0)
            if lhrs > 0 and lamount > 0:
                body_rates.add(round(lamount / lhrs))

        est_body_rate = max(body_rates) if body_rates else 0
        std_body = labor.get("body", 0)
        std_paint = labor.get("paint", 0)
        std_frame = labor.get("frame", 0)
        std_mech = labor.get("mech", 0)

        diffs = []
        if est_body_rate > 0 and est_body_rate != std_body:
            diffs.append(f"Body: est ${est_body_rate}/hr vs standard ${std_body}/hr")

        if tax and tax.get("combined", 0) > 0:
            std_tax = tax["combined"]
            est_tax = ctx.metadata.get("estimate_tax_rate")
            if est_tax and abs(std_tax * 100 - est_tax) > 0.1:
                diffs.append(f"Tax: est {est_tax:.1%} vs standard {std_tax:.1%}")

        if diffs:
            results.append(RuleResult(
                rule_id=self.rule_id,
                category=self.category,
                severity="high",
                description=f"ZIP {zip_code}: rate/tax discrepancy — {'; '.join(diffs)}",
                line_numbers=[],
                summary=f"ZIP {zip_code}: rate/tax discrepancy — {'; '.join(diffs)}",
                detail=(
                    f"Verify estimate rates match ZIP {zip_code} standard. "
                    f"NatGen: never overrule CCC labor rates. Document any differences."
                ),
                action=(
                    f"Standard rates for ZIP {zip_code}: Body ${std_body}/hr, Paint ${std_paint}/hr, "
                    f"Frame ${std_frame}/hr, Mech ${std_mech}/hr. "
                    f"ESTIMATE DIFFERS: {'; '.join(diffs)}"
                ),
            ))

        return results
