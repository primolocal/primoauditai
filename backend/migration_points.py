import os
import re

def process(filepath):
    with open(filepath, 'r') as f:
        content = f.read()

    def replacer(match):
        rule_id = match.group(1)
        blk = match.group(0)
        
        cat = "carrier_compliance"
        pts = 5
        
        if rule_id in ["R001", "R005", "R006", "R007", "R029"]:
            cat = "documentation_readiness"
            pts = 5 if rule_id != "R029" else 10
        elif rule_id in ["R008", "R025"]:
            cat = "structural_integrity"
            pts = 20 if rule_id == "R008" else 15
        elif rule_id in ["R004", "R015", "R016", "R018", "R023", "R024", "R026", "R028"]:
            cat = "line_item_support"
            pts = 10 if rule_id not in ["R018", "R004"] else 20
        elif rule_id in ["R011", "R017"]:
            cat = "parts_accuracy"
            pts = 20 if rule_id == "R011" else 10
        elif rule_id in ["R009", "R012", "R013", "R014", "R030"]:
            cat = "labor_reasonableness"
            pts = 10
        elif rule_id in ["R027"]:
            pts = 10
            
        blk = re.sub(r'category:\s*"[^"]*",', f'category: "{cat}",\n    points: {pts},', blk)
        return blk

    content = re.sub(r'rule_id:\s*"(R\d{3})",.*?(?=trigger_conditions)', replacer, content, flags=re.DOTALL)
    
    with open(filepath, 'w') as f:
        f.write(content)

process('src/lib/rules/tier1.ts')
process('src/lib/rules/tier2.ts')
process('src/lib/rules/tier3.ts')
print("Successfully migrated Rule definitions.")
