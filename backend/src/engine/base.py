"""
Rules engine base layer — the contract every rule implements.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.engine.context import AuditContext

@dataclass(frozen=True)
class RuleResult:
    """
    The output of a single rule evaluation.

    Frozen dataclass — immutable once created. Rules return these,
    the engine groups them, the UI displays them.
    """
    rule_id: str
    category: str
    severity: str
    description: str
    line_numbers: list[int] = field(default_factory=list)
    confidence: float = field(default=1.0)
    applies: bool = True
    override_reason: str | None = None

    # Rich display fields (optional — rules may provide for UI rendering)
    title: str | None = None
    summary: str | None = None
    detail: str | None = None
    action: str | None = None
    status: str = "unreviewed"

    def __post_init__(self) -> None:
        # Confidence must be 0.0-1.0
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence must be 0.0-1.0, got {self.confidence}")

    @property
    def affected_lines(self) -> list[int]:
        """Alias for line_numbers — backward compatible with v1 terminology."""
        return self.line_numbers


class BaseRule(ABC):
    """
    Abstract base class for all audit rules.

    Every rule implements two methods:
    - applies(ctx) → bool: Should this rule evaluate against this audit context?
    - evaluate(ctx) → List[RuleResult]: Run the rule, return findings.

    Rules are auto-discovered by the engine via importlib. Adding a rule
    = create a file + subclass BaseRule. No engine edits needed.
    """

    rule_id: str = ""
    category: str = ""
    description: str = ""

    @abstractmethod
    def applies(self, ctx: AuditContext) -> bool:
        """Return True if this rule should evaluate against the given context."""
        raise NotImplementedError

    @abstractmethod
    def evaluate(self, ctx: AuditContext) -> list[RuleResult]:
        """Evaluate the rule and return a list of findings (may be empty)."""
        raise NotImplementedError

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {self.rule_id}>"
