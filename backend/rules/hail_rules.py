"""
Hail/PDR-specific rules for supplement auditing.
Uses Dent Wizard Hail Pricing Matrix for price verification.
"""
from typing import List
import re
from audit_context import AuditContext
from rules.base import BaseRule, RuleResult
from rules.dent_wizard_matrix import lookup_price, PANEL_ALIASES


class PDRIncreaseVerificationRule(BaseRule):
    """
    HAIL_001: On hail supplements, verify PDR amounts against Dent Wizard matrix.
    Flags markup percentages and missing documentation.
    Auditor jumps straight to the exact line number.
    """
    rule_id = "HAIL_001"
    title = "PDR — Verify Against Dent Wizard Matrix"
    category = "line_item_support"
    severity = "high"

    def applies(self, ctx: AuditContext) -> bool:
        return True

    def evaluate(self, ctx: AuditContext) -> List[RuleResult]:
        results = []
        for line in ctx.get_all_lines():
            if line.get("is_header"):
                continue

            op_label = str(line.get("operation_label", "")).lower()
            desc = str(line.get("description", "")).lower()
            supplement = str(line.get("supplement", ""))

            if op_label != "pdr":
                continue

            line_no = line.get("line_no", "?")
            price = line.get("financial_signature", {}).get("part_price", 0)

            # Skip $0 PDR lines (included/header items)
            if price == 0:
                continue

            markup_match = re.search(r'\+(\d+)%', desc)
            has_markup = bool(markup_match)
            markup_pct = int(markup_match.group(1)) if markup_match else 0

            # Identify panel for matrix lookup (check longer aliases first, exclude note text)
            desc_main = desc.split("[")[0] if "[" in desc else desc
            panel_type = ""
            sorted_aliases = sorted(PANEL_ALIASES.items(), key=lambda x: -len(x[0]))
            for alias, key in sorted_aliases:
                if alias in desc_main:
                    panel_type = key
                    break

            matrix_ref = f" | Matrix: {panel_type}" if panel_type else ""
            
            # Try to look up matrix price from dent count and coin size in description
            matrix_price = None
            dent_count = None
            coin_size = None
            
            # Extract dent count and coin size from notes like "PDR 30 quarter" or "PDR 150 nickel"
            dent_match = re.search(r'(\d+)\s*(?:dent|quarter|nickel|dime|half)', desc)
            if not dent_match:
                dent_match = re.search(r'pdr\s+(\d+)', desc)
            if dent_match:
                try:
                    dent_count = int(dent_match.group(1))
                except ValueError:
                    pass
            
            for coin in ["quarter", "nickel", "dime", "half dollar", "half"]:
                if coin in desc:
                    coin_size = coin.replace(" dollar", "").upper()
                    if coin_size == "HALF":
                        coin_size = "HALF"
                    elif coin_size == "NICKEL":
                        coin_size = "NICKEL"
                    elif coin_size == "DIME":
                        coin_size = "DIME"
                    elif coin_size == "QUARTER":
                        coin_size = "QUARTER"
                    break
            
            if panel_type and dent_count and coin_size:
                from rules.dent_wizard_matrix import lookup_price
                matrix_price = lookup_price(panel_type, dent_count, coin_size)
            
            matrix_ref = ""
            if panel_type:
                if matrix_price:
                    matrix_ref = f" | Matrix: {panel_type} ${matrix_price}"
                    if price > 0 and matrix_price != price:
                        diff = price - matrix_price
                        matrix_ref += f" (est ${price:.0f}, diff ${diff:+.0f})"
                else:
                    matrix_ref = f" | Matrix: {panel_type}"

            if has_markup:
                summary = (
                    f"PDR L{line_no}: +{markup_pct}% markup — "
                    f"verify photos/scope sheet document increase{matrix_ref}"
                )
            else:
                summary = (
                    f"PDR L{line_no}: ${price:.2f} — "
                    f"verify amount vs Dent Wizard matrix{matrix_ref}"
                )

            why = (
                f"PDR on supplement line {line_no} (${price:.2f}). "
                f"NatGen requires: (1) hail photos with striped/checker board, "
                f"(2) completed scope sheet or hail matrix, "
                + (f"(3) +{markup_pct}% markup justification. " if has_markup else
                   f"(3) amount matches Dent Wizard matrix for dent count/size. ")
                + f"Cross-reference the Dent Wizard Hail Price Sheet NGIC."
            )

            results.append(RuleResult(
                rule_id=self.rule_id, title=self.title,
                category=self.category, severity=self.severity,
                financial_impact=price, affected_lines=[line_no],
                summary=summary, why_flagged=why,
                recommended_actions=(
                    f"1. Open Dent Wizard Hail Price Sheet NGIC. "
                    f"2. Find {panel_type or 'panel'} for dent count/size. "
                    f"3. Verify PDR amount on line {line_no}. "
                    + (f"4. Confirm +{markup_pct}% markup justified." if has_markup else
                       f"4. Confirm amount matches matrix or document variance.")
                ),
                debug_context={
                    "panel_type": panel_type,
                    "pdr_price": price,
                    "markup_pct": markup_pct,
                }
            ))

        return results
