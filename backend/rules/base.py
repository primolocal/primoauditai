from abc import ABC, abstractmethod
from typing import List, Optional, Literal
from pydantic import BaseModel, Field
from audit_context import AuditContext

class RuleResult(BaseModel):
    rule_id: str
    title: str
    category: str
    severity: Literal['high', 'medium', 'low']
    confidence: float = 1.0
    financial_impact: float = 0.0
    affected_lines: List[int] = Field(default_factory=list)
    evidence_refs: List[dict] = Field(default_factory=list)
    summary: str
    why_flagged: str
    recommended_actions: str
    status: Literal['unreviewed', 'resolved', 'overridden', 'review_later'] = 'unreviewed'
    debug_context: Optional[dict] = None

class BaseRule(ABC):
    rule_id: str
    title: str
    category: str
    severity: str

    @abstractmethod
    def applies(self, ctx: AuditContext) -> bool:
        """Determines if the rule should evaluate the context."""
        pass

    @abstractmethod
    def evaluate(self, ctx: AuditContext) -> List[RuleResult]:
        """Runs evaluation and generates findings."""
        pass
