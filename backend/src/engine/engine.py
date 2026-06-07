"""
RulesEngine — auto-discovery, singleton cache, per-rule error isolation.
"""
from typing import Dict, List, Optional

from src.engine.base import BaseRule, RuleResult
from src.engine.context import AuditContext


class RulesEngine:
    """
    Discovers, caches, and executes all audit rules.

    - Auto-discovery: loads all BaseRule subclasses from the domains package
    - Singleton: rules discovered once, 0ms on subsequent runs
    - Per-rule isolation: one broken rule does NOT crash the audit

    Usage:
        engine = get_engine()  # singleton
        results = engine.run_all(audit_context)
    """

    def __init__(self, _rules: Optional[List[BaseRule]] = None) -> None:
        if _rules is not None:
            self._rules = _rules
        else:
            from src.engine.discovery import discover_rules
            self._rules = discover_rules("src.domains")

    def run_all(self, ctx: AuditContext) -> Dict[str, List[RuleResult]]:
        """
        Run all applicable rules against the audit context.

        Returns a dict mapping rule class name to list of RuleResults.
        Only includes rules that both (a) apply and (b) produce findings.
        """
        results: Dict[str, List[RuleResult]] = {}

        for rule in self._rules:
            try:
                if not rule.applies(ctx):
                    continue

                findings = rule.evaluate(ctx)
                if findings:
                    results[rule.__class__.__name__] = findings
            except Exception:
                # Per-rule error isolation: log and continue
                # In production, this would log to structured logging
                continue

        return results

    def rule_count(self) -> int:
        """Return the number of loaded rules."""
        return len(self._rules)

    def list_rules(self) -> List[str]:
        """Return list of loaded rule IDs."""
        return [r.rule_id for r in self._rules]


# --- Singleton ---
_engine_instance: Optional[RulesEngine] = None


def get_engine() -> RulesEngine:
    """
    Return the singleton RulesEngine instance.

    Rules are discovered once on first call. Subsequent calls return
    the cached instance with 0ms overhead.
    """
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = RulesEngine()
    return _engine_instance


def reset_engine() -> None:
    """Reset the singleton (useful for testing)."""
    global _engine_instance
    _engine_instance = None
