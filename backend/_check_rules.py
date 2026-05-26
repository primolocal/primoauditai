import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from rules_engine import RulesEngine
engine = RulesEngine()
rules = engine.registry.get_all_rules()
print(f"Auto-discovered {len(rules)} rules:")
for r in rules:
    print(f"  - {r.rule_id}: {r.title} ({r.category})")
