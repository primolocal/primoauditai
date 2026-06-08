"""Learning Threshold Rule — flags any automated finding where confidence is below 95%.
"""
from __future__ import annotations

from src.engine.base import BaseRule, RuleResult
from src.engine.context import AuditContext


class LowConfidenceReviewRule(BaseRule):
    """LEARN_001: Human review required for any finding below 95% confidence."""
    rule_id = "LEARN_001"
    category = "carrier_compliance"
    description = "Anything less than 95% confidence on guideline application requires human review"
    severity = "high"
    MIN_CONFIDENCE = 0.95

    def applies(self, ctx: AuditContext) -> bool:
        return True

    def evaluate(self, ctx: AuditContext) -> list[RuleResult]:
        results = []
        for line in ctx.get_all_lines():
            if line.get("is_header"):
                continue
            confidence = line.get("confidence", 1.0)
            if isinstance(confidence, (int, float)) and confidence < self.MIN_CONFIDENCE:
                line_no = line.get("line_no", 0) or 0
                results.append(RuleResult(
                    rule_id=self.rule_id,
                    category=self.category,
                    severity="high",
                    description=(
                        f"Guideline applied at {confidence:.0%} confidence — "
                        f"below {self.MIN_CONFIDENCE:.0%} threshold. Manual review required."
                    ),
                    line_numbers=[line_no],
                    confidence=confidence,
                    summary=f"Low confidence finding at L{line_no} — human review required.",
                    detail=(
                        f"Per audit policy, any guideline application below "
                        f"{self.MIN_CONFIDENCE:.0%} confidence must be reviewed "
                        f"by a human auditor. This finding has {confidence:.0%} confidence."
                    ),
                    action=(
                        "Review this finding manually. If correct, confirm. "
                        "If incorrect, overturn with reason code. "
                        "This feedback trains the rules engine."
                    ),
                ))

        return results
