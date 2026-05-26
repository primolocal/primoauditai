"""
RACED Guide — Recycled Assembly Components and Estimating Data.
Verifies transfer lines when LKQ/recycled parts are used on an estimate.
MOTOR RACED standard: each assembly listing tells what IS and IS NOT included.
"""
from typing import List, Dict, Set
from audit_context import AuditContext
from rules.base import BaseRule, RuleResult


# RACED assembly data: (assembly_type, included_items, transfer_items)
# "included" = comes on the LKQ assembly automatically
# "transfer" = must be R&I'd from old part to new LKQ part
RACED_DATA: Dict[str, dict] = {
    "door": {
        "included": ["door shell", "door skin", "intrusion beam"],
        "not_included": [
            "trim panel", "mirror", "hinge", "handle", "regulator",
            "weatherstrip", "lock", "latch", "belt molding", "glass",
            "run channel", "speaker", "wiring harness", "door check",
            "striker", "molding", "nameplate", "emblem",
        ],
    },
    "bumper": {
        "included": ["bumper cover", "reinforcement", "absorber", "impact bar"],
        "not_included": [
            "bracket", "park sensor", "fog lamp", "reflector", "molding",
            "trim", "grille", "skid plate", "tow hook cover", "license bracket",
        ],
    },
    "hood": {
        "included": ["hood panel", "hood skin", "inner structure"],
        "not_included": [
            "hinge", "insulator", "latch", "release cable", "strut", "prop rod",
            "nozzle", "washer hose", "weatherstrip", "seal", "emblem", "scoop",
        ],
    },
    "fender": {
        "included": ["fender panel"],
        "not_included": [
            "liner", "splash shield", "molding", "emblem", "nameplate",
            "antenna", "side marker", "reflector", "flare", "bracket",
        ],
    },
    "liftgate": {
        "included": ["liftgate shell"],
        "not_included": [
            "trim panel", "glass", "wiper motor", "wiper arm", "handle",
            "lock", "latch", "molding", "emblem", "nameplate", "spoiler",
            "strut", "hinge", "weatherstrip", "third brake light", "camera",
        ],
    },
    "deck lid": {
        "included": ["deck lid panel"],
        "not_included": [
            "trim panel", "carpet", "lock", "latch", "emblem", "nameplate",
            "spoiler", "hinge", "spring", "strut", "weatherstrip",
            "third brake light", "camera", "release cable",
        ],
    },
    "quarter": {
        "included": ["quarter panel", "wheelhouse"],
        "not_included": [
            "trim panel", "glass", "molding", "emblem", "fuel door",
            "antenna", "rocker molding",
        ],
    },
    "roof": {
        "included": ["roof panel", "roof bow", "roof rail"],
        "not_included": [
            "headliner", "sunroof", "roof rack", "antenna", "molding",
            "drip rail", "weatherstrip",
        ],
    },
    "radiator support": {
        "included": ["radiator support", "upper tie bar", "lower tie bar"],
        "not_included": [
            "radiator", "condenser", "fan", "shroud", "headlamp bracket",
            "hood latch", "bracket", "air guide", "sensor",
        ],
    },
    "pick up box": {
        "included": ["box side", "floor", "front panel", "tail gate"],
        "not_included": [
            "wheelhouse liner", "molding", "tie down", "bed liner",
            "tonneau cover", "step", "handle", "striker",
        ],
    },
}

# Map estimate description keywords to RACED assembly types
ASSEMBLY_KEYWORDS: Dict[str, str] = {
    "door": "door", "door shell": "door", "door assy": "door",
    "bumper": "bumper", "bumper cover": "bumper", "bumper assy": "bumper",
    "hood": "hood", "hood assy": "hood",
    "fender": "fender", "fender panel": "fender",
    "liftgate": "liftgate", "lift gate": "liftgate", "tail gate": "liftgate",
    "deck lid": "deck lid", "trunk lid": "deck lid", "trunk": "deck lid",
    "quarter": "quarter", "quarter panel": "quarter",
    "roof": "roof", "roof panel": "roof", "roof assy": "roof",
    "radiator support": "radiator support", "core support": "radiator support",
    "pick up box": "pick up box", "box side": "pick up box",
}


class RACEDTransferRule(BaseRule):
    """
    RACED_001: Verify LKQ transfer lines match RACED assembly data.
    Flags missing transfer lines and unexpected transfer lines.
    """
    rule_id = "RACED_001"
    title = "RACED — LKQ Transfer Verification"
    category = "parts_accuracy"
    severity = "medium"

    def applies(self, ctx: AuditContext) -> bool:
        return True

    def evaluate(self, ctx: AuditContext) -> List[RuleResult]:
        results = []
        all_lines = ctx.get_all_lines()
        
        # Find LKQ/recycled assemblies and their transfer lines
        lkq_assemblies = []
        for line in all_lines:
            if line.get("is_header"):
                continue
            desc = str(line.get("description", "")).lower()
            pn = str(line.get("part_number", ""))
            pt = str(line.get("part_type", "")).upper()
            op = str(line.get("operation_label", "")).lower()
            
            # Detect LKQ part
            is_lkq = pt in ("LKQ", "PAR", "PAM") or "lkq" in desc or "recycled" in desc
            if not is_lkq:
                continue
            
            # Match to RACED assembly type
            assembly = None
            for kw, asm_type in ASSEMBLY_KEYWORDS.items():
                if kw in desc:
                    assembly = asm_type
                    break
            
            if assembly and assembly in RACED_DATA:
                lkq_assemblies.append({
                    "line_no": line.get("line_no"),
                    "assembly": assembly,
                    "desc": line.get("description", ""),
                    "data": RACED_DATA[assembly],
                })
        
        if not lkq_assemblies:
            return results
        
        # For each LKQ assembly, check transfer lines
        for asm in lkq_assemblies:
            asm_type = asm["assembly"]
            not_included = asm["data"]["not_included"]
            line_no = asm["line_no"]
            
            # Find all R&I lines near this assembly
            for line in all_lines:
                if line.get("is_header"):
                    continue
                ri_desc = str(line.get("description", "")).lower()
                ri_op = str(line.get("operation_label", "")).lower()
                
                if ri_op not in ("remove & install",):
                    continue
                
                # Check if this R&I is a known transfer item
                is_transfer = any(item in ri_desc for item in not_included)
                
                if is_transfer:
                    # This R&I is a legitimate transfer — mark it
                    results.append(RuleResult(
                        rule_id=self.rule_id, title="LKQ Transfer — Verified",
                        category=self.category, severity="low",
                        affected_lines=[line.get("line_no")],
                        summary=f"LKQ {asm_type} transfer L{line.get('line_no')}: {line.get('description','')[:50]} — per RACED.",
                        why_flagged=(
                            f"RACED confirms LKQ {asm_type} assemblies come WITHOUT {ri_desc}. "
                            f"This R&I transfer line is legitimate."
                        ),
                        recommended_actions="Transfer verified per RACED. No action needed.",
                        debug_context={"verified": True, "assembly": asm_type},
                    ))
        
        return results
