#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rules_engine import RulesEngine
e = RulesEngine()
count = len(e.registry.get_all_rules())
print(f"Engine created with {count} rules")

# Print all rule IDs
for i, rule in enumerate(e.registry.get_all_rules()):
    print(f"  {i+1}. {rule.rule_id}: {rule.title}")

# Test singleton — second instantiation should be instant
import time
start = time.time()
e2 = RulesEngine()
elapsed = (time.time() - start) * 1000
print(f"\nSecond instantiation took {elapsed:.2f}ms (singleton working: {e.registry is e2.registry})")

print(f"\nSUCCESS: {count} rules loaded")
