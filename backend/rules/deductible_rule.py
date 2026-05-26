"""Deductible verification — must be listed on collision/comprehensive estimates."""
from typing import List
import re
from audit_context import AuditContext
from rules.base import BaseRule, RuleResult


class DeductibleRequiredRule(BaseRule):
    """CHECK_005: Collision/Comprehensive estimates must show deductible in totals."""
    rule_id = "CHECK_005"
    title = "Deductible — Must Be Listed"
    category = "documentation_readiness"
    severity = "high"

    _COLLISION_TYPES = {"collision", "comprehensive", "comp"}

    def applies(self, ctx: AuditContext) -> bool:
        return True

    def evaluate(self, ctx: AuditContext) -> List[RuleResult]:
        results = []
        meta = ctx.raw_data.get("claim_meta", {})

        # Check type of loss
        loss_type = str(meta.get("loss_type", meta.get("type_of_loss", ""))).lower().strip()
        if not loss_type:
            return results

        is_collision = any(t in loss_type for t in self._COLLISION_TYPES)
        if not is_collision:
            return results

        # Check if deductible appears anywhere in the estimate data
        all_text = ""
        for panel in ctx.raw_data.get("claim", {}).get("panels", []):
            for row in panel.get("rows", []):
                all_text += " " + str(row.get("description", ""))

        # Look for deductible in totals or line items
        has_deductible = (
            "deductible" in all_text.lower()
            or "deduct" in all_text.lower()
            or any(
                row.get("row_type") == "deductible"
                or str(row.get("description", "")).lower().startswith("deduct")
                for panel in ctx.raw_data.get("claim", {}).get("panels", [])
                for row in panel.get("rows", [])
            )
        )

        if not has_deductible:
            results.append(RuleResult(
                rule_id=self.rule_id,
                title=self.title,
                category=self.category,
                severity=self.severity,
                affected_lines=[],
                summary=f"{loss_type.title()} claim — deductible must be listed in estimate totals (even if $0).",
                why_flagged=(
                    f"{loss_type.title()} claims require the deductible to appear in the estimate "
                    f"summary/totals section. Even if the deductible is $0, it must be listed. "
                    f"Missing deductible is a revision trigger."
                ),
                recommended_actions="Add deductible to estimate totals. If $0, enter $0 — it must still appear.",
                status="unreviewed",
            ))

        return results
