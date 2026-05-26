"""
Rules Engine — evaluates all registered rules against audit context.
Rules are auto-discovered from the rules/ directory using importlib scanning.
"""
import importlib
import pkgutil
import os
from typing import Dict, Any, List

from audit_context import AuditContext
from rules.registry import RuleRegistry
from rules.base import BaseRule


def _discover_rules() -> List[BaseRule]:
    """
    Auto-discover all rule classes by scanning the rules/ package.
    Any class that subclasses BaseRule (and isn't BaseRule itself) is instantiated
    and returned. Adding a new rule = just create the file + class, no engine edits needed.
    """
    import rules as rules_pkg

    rule_instances = []

    rules_dir = os.path.dirname(rules_pkg.__file__)
    for _, module_name, _ in pkgutil.iter_modules([rules_dir]):
        # Skip base/registry modules
        if module_name in ('base', 'registry'):
            continue
        try:
            mod = importlib.import_module(f"rules.{module_name}")
        except Exception as e:
            # Silently skip modules that fail to import (missing deps, etc.)
            continue

        for attr_name in dir(mod):
            attr = getattr(mod, attr_name)
            if (
                isinstance(attr, type)
                and issubclass(attr, BaseRule)
                and attr is not BaseRule
                and not attr.__name__.startswith('_')
            ):
                try:
                    rule_instances.append(attr())
                except Exception:
                    pass  # Skip rules that can't be instantiated (e.g., abstract subclasses)

    return rule_instances


# Module-level singleton cache — rules discovered once, reused forever
_discovered_rules: List[BaseRule] = []
_discovered_rules_lock = False


def _get_or_discover_rules() -> List[BaseRule]:
    """Return cached rules, discovering them on first call only."""
    global _discovered_rules, _discovered_rules_lock
    if not _discovered_rules_lock:
        _discovered_rules = _discover_rules()
        _discovered_rules_lock = True
    return _discovered_rules


class RulesEngine:
    def __init__(self):
        self.registry = RuleRegistry()
        # Rules are auto-discovered once (module-level cache), then registered
        for rule in _get_or_discover_rules():
            self.registry.register(rule)

    def evaluate_estimate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        ctx = AuditContext(data)

        base_findings = []
        natgen_findings = []

        # Evaluate all rules with per-rule error isolation — one broken rule won't crash the audit
        for rule in self.registry.get_all_rules():
            try:
                if rule.applies(ctx):
                    results = rule.evaluate(ctx)
                else:
                    continue
            except Exception as e:
                import logging
                logging.getLogger("primoaudit.rules").error(
                    f"Rule {rule.rule_id} failed during evaluation: {e}", exc_info=True
                )
                continue

            for res in results:
                # Convert to legacy parsing dictionary format for adapter
                f_dict = res.model_dump()
                f_dict["message"] = f_dict["summary"]  # Map summary to legacy message
                if f_dict["affected_lines"]:
                    f_dict["line_no"] = f_dict["affected_lines"][0]

                if "NATGEN" in rule.rule_id:
                    natgen_findings.append(f_dict)
                else:
                    base_findings.append(f_dict)

        from scoring import ScoringService
        from narrative import NarrativeService

        all_findings = base_findings + natgen_findings
        score_data = ScoringService.calculate(all_findings)
        narrative_data = NarrativeService.generate(all_findings, score_data)

        data["audit"] = {
            **score_data,
            "base_findings": base_findings,
            "carrier_overlays": {
                "natgen": {
                    "findings": natgen_findings
                }
            },
            "rows_needing_review": []
        }

        data["narrative"] = narrative_data

        return data
