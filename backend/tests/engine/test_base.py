"""
Tests for the rules engine base layer.
RED-GREEN-REFACTOR: every new behavior starts with a failing test.
"""
from typing import List
from uuid import UUID
import pytest

from src.engine.base import BaseRule, RuleResult
from src.engine.context import AuditContext


class TestRuleResult:
    """Test the RuleResult dataclass."""

    def test_rule_result_creation(self) -> None:
        """RuleResult stores all required fields."""
        result = RuleResult(
            rule_id="AUDIT_001",
            category="AUDIT",
            severity="HIGH",
            description="Labor rate above carrier threshold",
            line_numbers=[42, 43],
            confidence=0.95,
        )
        assert result.rule_id == "AUDIT_001"
        assert result.category == "AUDIT"
        assert result.severity == "HIGH"
        assert result.description == "Labor rate above carrier threshold"
        assert result.line_numbers == [42, 43]
        assert result.confidence == 0.95
        assert result.applies is True
        assert result.override_reason is None

    def test_rule_result_default_applies(self) -> None:
        """Default applies=True — must explicitly set False."""
        result = RuleResult(
            rule_id="TEST_001",
            category="TEST",
            severity="LOW",
            description="Test rule",
        )
        assert result.applies is True
        assert result.line_numbers == []

    def test_rule_result_override(self) -> None:
        """Override sets applies=False with reason."""
        result = RuleResult(
            rule_id="AUDIT_001",
            category="AUDIT",
            severity="HIGH",
            description="Override reason",
            applies=False,
            override_reason="Auditor verified — not applicable for this claim type",
        )
        assert result.applies is False
        assert result.override_reason == "Auditor verified — not applicable for this claim type"

    def test_rule_result_confidence_bounds(self) -> None:
        """Confidence must be 0.0-1.0."""
        with pytest.raises(ValueError):
            RuleResult(
                rule_id="BAD",
                category="BAD",
                severity="LOW",
                description="bad",
                confidence=1.5,
            )
        with pytest.raises(ValueError):
            RuleResult(
                rule_id="BAD",
                category="BAD",
                severity="LOW",
                description="bad",
                confidence=-0.1,
            )


class TestBaseRule:
    """Test the BaseRule abstract class."""

    def test_base_rule_cannot_instantiate(self) -> None:
        """Abstract class cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseRule()


class ConcreteRule(BaseRule):
    """Test double — concrete rule implementation."""

    rule_id = "TEST_001"
    category = "TEST"
    description = "Test concrete rule"

    def applies(self, ctx: AuditContext) -> bool:
        return len(ctx.lines) > 0

    def evaluate(self, ctx: AuditContext) -> List[RuleResult]:
        return [
            RuleResult(
                rule_id=self.rule_id,
                category=self.category,
                severity="LOW",
                description=self.description,
                line_numbers=[1],
                confidence=0.75,
            )
        ]


class TestConcreteRule:
    """Test a working concrete rule against BaseRule."""

    def test_concrete_applies_when_lines_present(self) -> None:
        """Rule applies if context has lines."""
        ctx = AuditContext(lines=[{"line_no": 1, "description": "Test"}])
        rule = ConcreteRule()
        assert rule.applies(ctx) is True

    def test_concrete_not_applies_when_empty(self) -> None:
        """Rule does NOT apply if context has no lines."""
        ctx = AuditContext(lines=[])
        rule = ConcreteRule()
        assert rule.applies(ctx) is False

    def test_concrete_evaluate_returns_result(self) -> None:
        """Evaluate returns a RuleResult with correct fields."""
        ctx = AuditContext(lines=[{"line_no": 1, "description": "Test"}])
        rule = ConcreteRule()
        results = rule.evaluate(ctx)
        assert len(results) == 1
        assert results[0].rule_id == "TEST_001"
        assert results[0].confidence == 0.75
