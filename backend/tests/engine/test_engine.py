"""
Tests for rules engine discovery and singleton.
"""
import importlib
import sys
import tempfile
from pathlib import Path

import pytest

from src.engine.base import BaseRule, RuleResult
from src.engine.context import AuditContext
from src.engine.discovery import discover_rules
from src.engine.engine import RulesEngine, get_engine, reset_engine


@pytest.fixture(autouse=True)
def cleanup_modules():
    """Clean up test modules from sys.modules after each test."""
    before = set(sys.modules.keys())
    yield
    after = set(sys.modules.keys())
    for mod in after - before:
        if "test_rules" in mod or "dummy" in mod:
            del sys.modules[mod]
    reset_engine()


class TestDiscoverRules:
    """Test importlib-based rule auto-discovery."""

    def test_discovers_concrete_rules(self, tmp_path: Path) -> None:
        """Finds concrete BaseRule subclasses in a directory."""
        # Create temp rule module
        rules_dir = tmp_path / "test_rules"
        rules_dir.mkdir()
        (rules_dir / "__init__.py").write_text("")
        (rules_dir / "test_rule.py").write_text("""
from src.engine.base import BaseRule, RuleResult
from src.engine.context import AuditContext
from typing import List

class DummyRule(BaseRule):
    rule_id = "DUMMY_001"
    category = "TEST"
    description = "A dummy rule for testing"

    def applies(self, ctx: AuditContext) -> bool:
        return True

    def evaluate(self, ctx: AuditContext) -> List[RuleResult]:
        return [RuleResult(
            rule_id=self.rule_id,
            category=self.category,
            severity="LOW",
            description=self.description,
        )]
""")
        # Add temp dir to sys.path
        sys.path.insert(0, str(tmp_path))
        try:
            rules = discover_rules("test_rules")
            assert len(rules) == 1
            assert rules[0].rule_id == "DUMMY_001"
        finally:
            sys.path.remove(str(tmp_path))

    def test_ignores_abstract_base(self, tmp_path: Path) -> None:
        """BaseRule itself is NOT included in discovered rules."""
        rules_dir = tmp_path / "test_rules"
        rules_dir.mkdir()
        (rules_dir / "__init__.py").write_text("")
        (rules_dir / "only_base.py").write_text("""
from src.engine.base import BaseRule
""")
        sys.path.insert(0, str(tmp_path))
        try:
            rules = discover_rules("test_rules")
            assert len(rules) == 0
        finally:
            sys.path.remove(str(tmp_path))

    def test_ignores_non_rule_classes(self, tmp_path: Path) -> None:
        """Classes not inheriting BaseRule are skipped."""
        rules_dir = tmp_path / "test_rules"
        rules_dir.mkdir()
        (rules_dir / "__init__.py").write_text("")
        (rules_dir / "other.py").write_text("""
class NotARule:
    pass
""")
        sys.path.insert(0, str(tmp_path))
        try:
            rules = discover_rules("test_rules")
            assert len(rules) == 0
        finally:
            sys.path.remove(str(tmp_path))


class TestRulesEngine:
    """Test the RulesEngine singleton with auto-discovery."""

    def test_runs_all_rules(self) -> None:
        """Engine runs all loaded rules against a context."""
        engine = RulesEngine(_rules=[AlwaysFiresRule()])
        ctx = AuditContext(lines=[{"line_no": 1}])
        results = engine.run_all(ctx)
        assert "AlwaysFiresRule" in results
        assert len(results["AlwaysFiresRule"]) == 1

    def test_skips_non_applicable_rules(self) -> None:
        """Rules where applies() returns False are skipped."""
        engine = RulesEngine(_rules=[NeverAppliesRule()])
        ctx = AuditContext(lines=[])
        results = engine.run_all(ctx)
        assert "NeverAppliesRule" not in results

    def test_per_rule_error_isolation(self) -> None:
        """One broken rule does NOT crash the engine."""
        engine = RulesEngine(_rules=[AlwaysFiresRule(), BrokenRule()])
        ctx = AuditContext(lines=[{"line_no": 1}])
        results = engine.run_all(ctx)
        assert "AlwaysFiresRule" in results
        assert "BrokenRule" not in results  # silenced, not crashed

    def test_empty_context(self) -> None:
        """Engine handles empty context gracefully."""
        engine = RulesEngine(_rules=[])
        ctx = AuditContext(lines=[])
        results = engine.run_all(ctx)
        assert results == {}


class TestSingleton:
    """Test the singleton pattern."""

    def test_same_instance(self) -> None:
        """get_engine() returns the same instance on repeat calls."""
        engine1 = get_engine()
        engine2 = get_engine()
        assert engine1 is engine2

    def test_rules_cached(self) -> None:
        """Rules are discovered once and cached."""
        engine1 = get_engine()
        engine2 = get_engine()
        assert engine1._rules is engine2._rules


# --- Test doubles ---

class AlwaysFiresRule(BaseRule):
    rule_id = "ALWAYS_001"
    category = "TEST"
    description = "Always fires"

    def applies(self, ctx: AuditContext) -> bool:
        return True

    def evaluate(self, ctx: AuditContext) -> list:
        return [RuleResult(
            rule_id=self.rule_id,
            category=self.category,
            severity="LOW",
            description=self.description,
        )]


class NeverAppliesRule(BaseRule):
    rule_id = "NEVER_001"
    category = "TEST"
    description = "Never applies"

    def applies(self, ctx: AuditContext) -> bool:
        return False

    def evaluate(self, ctx: AuditContext) -> list:
        return []


class BrokenRule(BaseRule):
    rule_id = "BROKEN_001"
    category = "TEST"
    description = "Always crashes"

    def applies(self, ctx: AuditContext) -> bool:
        return True

    def evaluate(self, ctx: AuditContext) -> list:
        raise RuntimeError("Simulated rule crash")
