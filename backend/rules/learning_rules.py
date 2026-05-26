"""
Learning Threshold Rule — flags any automated finding where the AI confidence
is below 95% for mandatory human review. This creates a feedback loop that
improves the rule engine over time.
"""
from typing import List
from audit_context import AuditContext
from rules.base import BaseRule, RuleResult


class LowConfidenceReviewRule(BaseRule):
    """
    ENSURES human review of any finding where the AI guideline application
    confidence is below 95%. This is the learning threshold — anything the
    system isn't certain about gets escalated.

    Per user directive: "anything less than 95% confidence on the application
    of a guideline — we need to go over so it can be learned."
    """
    rule_id = "LEARN_001"
    title = "Low Confidence — Human Review Required"
    category = "carrier_compliance"
    severity = "high"
    MIN_CONFIDENCE = 0.95

    def applies(self, ctx: AuditContext) -> bool:
        return True

    def evaluate(self, ctx: AuditContext) -> List[RuleResult]:
        results = []
        for line in ctx.get_all_lines():
            if line.get("is_header"):
                continue

            # Check for any finding with low confidence
            confidence = line.get("confidence", 1.0)
            if isinstance(confidence, (int, float)) and confidence < self.MIN_CONFIDENCE:
                results.append(RuleResult(
                    rule_id=self.rule_id,
                    title=self.title,
                    category=self.category,
                    severity="high",
                    affected_lines=[line.get("line_no")],
                    confidence=confidence,
                    summary=(
                        f"Guideline applied at {confidence:.0%} confidence — "
                        f"below {self.MIN_CONFIDENCE:.0%} threshold. "
                        "Manual review required for learning."
                    ),
                    why_flagged=(
                        f"Per audit policy, any guideline application below "
                        f"{self.MIN_CONFIDENCE:.0%} confidence must be reviewed "
                        f"by a human auditor. This finding has {confidence:.0%} confidence. "
                        f"Auditor should confirm or overturn so the system can learn."
                    ),
                    recommended_actions=(
                        "Review this finding manually. If correct, confirm. "
                        "If incorrect, overturn with reason code. "
                        "This feedback trains the rules engine."
                    ),
                    status="unreviewed",
                ))

        return results
