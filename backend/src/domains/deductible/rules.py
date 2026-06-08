"""Deductible verification — must be listed on collision/comprehensive estimates."""
from __future__ import annotations

from src.engine.base import BaseRule, RuleResult
from src.engine.context import AuditContext


class DeductibleRequiredRule(BaseRule):
    """CHECK_005: Collision/Comprehensive estimates must show deductible in totals."""
    rule_id = "CHECK_005"
    category = "documentation_readiness"
    description = "Deductible must be listed in estimate totals (even if $0)"
    severity = "high"

    _COLLISION_TYPES = {"collision", "comprehensive", "comp"}

    def applies(self, ctx: AuditContext) -> bool:
        return True

    def evaluate(self, ctx: AuditContext) -> list[RuleResult]:
        results = []
        loss_type = str(ctx.metadata.get("loss_type", ctx.metadata.get("type_of_loss", ""))).lower().strip()
        if not loss_type:
            return results

        is_collision = any(t in loss_type for t in self._COLLISION_TYPES)
        if not is_collision:
            return results

        # Check if deductible appears anywhere
        has_deductible = False
        for line in ctx.get_all_lines():
            desc = str(line.get("description", "")).lower()
            if desc.startswith("deduct") or line.get("row_type") == "deductible":
                has_deductible = True
                break

        if not has_deductible:
            results.append(RuleResult(
                rule_id=self.rule_id,
                category=self.category,
                severity=self.severity,
                description=f"{loss_type.title()} claim — deductible must be listed in estimate totals (even if $0).",
                line_numbers=[],
                summary=f"{loss_type.title()} claim — deductible must be listed in estimate totals (even if $0).",
                detail=(
                    f"{loss_type.title()} claims require the deductible to appear in the estimate "
                    f"summary/totals section. Even if the deductible is $0, it must be listed. "
                    f"Missing deductible is a revision trigger."
                ),
                action="Add deductible to estimate totals. If $0, enter $0 — it must still appear.",
            ))

        return results
