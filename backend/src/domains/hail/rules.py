"""Hail/PDR-specific rules for supplement auditing.
Flags PDR lines for Dent Wizard matrix verification.
"""
from __future__ import annotations

import re

from src.engine.base import BaseRule, RuleResult
from src.engine.context import AuditContext


class PDRIncreaseVerificationRule(BaseRule):
    """HAIL_001: On hail supplements, verify PDR amounts against Dent Wizard matrix."""
    rule_id = "HAIL_001"
    category = "line_item_support"
    description = "Verify PDR amounts against Dent Wizard Hail Pricing Matrix"
    severity = "high"

    def applies(self, ctx: AuditContext) -> bool:
        return True

    def evaluate(self, ctx: AuditContext) -> list[RuleResult]:
        results = []
        for line in ctx.get_all_lines():
            if line.get("is_header"):
                continue

            op_label = str(line.get("operation_label", "")).lower()
            desc = str(line.get("description", "")).lower()
            if op_label != "pdr":
                continue

            line_no = line.get("line_no", 0) or 0
            fs = line.get("financial_signature", {})
            price = fs.get("part_price", 0)

            if price == 0:
                continue

            markup_match = re.search(r'\+(\d+)%', desc)
            has_markup = bool(markup_match)
            markup_pct = int(markup_match.group(1)) if markup_match else 0

            if has_markup:
                summary = f"PDR L{line_no}: +{markup_pct}% markup — verify photos/scope sheet document increase"
            else:
                summary = f"PDR L{line_no}: ${price:.2f} — verify amount vs Dent Wizard matrix"

            why = (
                f"PDR on supplement line {line_no} (${price:.2f}). "
                f"NatGen requires: (1) hail photos with striped/checker board, "
                f"(2) completed scope sheet or hail matrix, "
                + (f"(3) +{markup_pct}% markup justification. " if has_markup else
                   f"(3) amount matches Dent Wizard matrix for dent count/size. ")
                + f"Cross-reference the Dent Wizard Hail Price Sheet NGIC."
            )

            results.append(RuleResult(
                rule_id=self.rule_id,
                category=self.category,
                severity=self.severity,
                description=summary,
                line_numbers=[line_no],
                summary=summary,
                detail=why,
                action=(
                    f"1. Open Dent Wizard Hail Price Sheet NGIC. "
                    f"2. Verify PDR amount on line {line_no}. "
                    + (f"3. Confirm +{markup_pct}% markup justified." if has_markup else
                       f"3. Confirm amount matches matrix or document variance.")
                ),
            ))

        return results
