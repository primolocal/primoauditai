from typing import List
from rules.base import BaseRule

class RuleRegistry:
    def __init__(self):
        self._rules: List[BaseRule] = []
        
    def register(self, rule: BaseRule):
        self._rules.append(rule)
        
    def get_all_rules(self) -> List[BaseRule]:
        return self._rules
        
    def get_rules_by_category(self, category: str) -> List[BaseRule]:
        return [r for r in self._rules if r.category == category]
