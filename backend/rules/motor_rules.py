"""
MOTOR Guide P-Page Rules — included/not-included operations per MOTOR Crash Estimating Data.
Uses MOTOR standards to determine if R&I is already included in a parent operation.
Flags only when R&I is likely NOT included and needs justification.
"""
from typing import List, Optional
from audit_context import AuditContext
from rules.base import BaseRule, RuleResult


# MOTOR included operations: when PARENT operation is performed, CHILD R&I is INCLUDED
# Format: ("parent_keyword", "child_keyword") — if parent is on estimate, child R&I is included
MOTOR_INCLUDED = [
    # Hood/Cowl area
    ("hood", "insulator"),
    ("hood", "hinge"),
    ("cowl", "cowl grille"),
    ("cowl", "wiper arm"),
    ("cowl", "wiper motor"),
    
    # Door area  
    ("door", "belt molding"),
    ("door", "weatherstrip"),
    ("door", "mirror"),
    ("door", "handle"),
    ("door", "lock"),
    ("door", "latch"),
    ("door", "regulator"),
    ("door", "trim panel"),
    ("door", "door glass"),
    ("door", "run channel"),
    
    # Bumper area
    ("bumper", "bracket"),
    ("bumper", "reinforcement"),
    ("bumper", "absorber"),
    ("bumper", "impact bar"),
    
    # Fender area
    ("fender", "liner"),
    ("fender", "splash shield"),
    
    # Roof area
    ("roof", "headliner"),
    ("roof", "sunroof"),
    ("roof", "roof rack"),
    ("roof", "antenna"),
    
    # Liftgate/tailgate
    ("liftgate", "trim panel"),
    ("liftgate", "glass"),
    ("liftgate", "wiper"),
    ("liftgate", "handle"),
    ("liftgate", "molding"),
    ("liftgate", "emblem"),
    ("liftgate", "nameplate"),
    ("tail gate", "trim panel"),
    ("tail gate", "handle"),
    
    # Quarter panel
    ("quarter", "trim panel"),
    ("quarter", "glass"),
    ("quarter", "molding"),
    
    # Lamps
    ("headlamp", "bracket"),
    ("headlamp", "mounting panel"),
    ("tail lamp", "bracket"),
    
    # Deck lid/trunk
    ("deck lid", "trim panel"),
    ("deck lid", "lock"),
    ("deck lid", "emblem"),
    ("deck lid", "nameplate"),
    ("deck lid", "spoiler"),
    ("trunk", "trim panel"),
    ("trunk", "carpet"),
    
    # Bed/box
    ("pick up box", "wheelhouse liner"),
    ("pick up box", "molding"),
    ("pick up box", "tie down"),
    
    # Radiator support
    ("radiator", "condenser"),
    ("radiator", "fan"),
    
    # Frame/structural  
    ("frame", "crossmember"),
    ("frame", "body mount"),
]


class MOTORIncludedRIRule(BaseRule):
    """
    MOTOR_001: Smart R&I check using MOTOR P-page knowledge.
    If R&I is included per MOTOR → skip silently.
    If R&I may not be included → low-confidence flag.
    If R&I is definitely NOT included → high-confidence flag.
    """
    rule_id = "MOTOR_001"
    title = "MOTOR P-Page — R&I Included Check"
    category = "line_item_support"
    severity = "low"

    def applies(self, ctx: AuditContext) -> bool:
        return True

    def evaluate(self, ctx: AuditContext) -> List[RuleResult]:
        results = []
        all_lines = ctx.get_all_lines()
        
        # Build set of REPLACE parent operations AND repair/PDR context
        # R&I is justified for repair access, not just replacement
        replace_parents = set()
        repair_panels = set()
        pdr_panels = set()
        
        for line in all_lines:
            desc = str(line.get("description", "")).lower()
            op = str(line.get("operation_label", "")).lower()
            
            # REPLACE ops get MOTOR included R&I
            if op == "replace":
                for keyword in ["hood", "door", "bumper", "fender", "roof", "quarter",
                               "deck lid", "trunk", "liftgate", "tail gate", "headlamp",
                               "tail lamp", "radiator", "frame", "cowl", "pick up box",
                               "lift gate", "lift"]:
                    if keyword in desc:
                        replace_parents.add(keyword)
            
            # REPAIR ops justify R&I for access
            if op in ("repair", "pdr", "overhaul", "remove & install"):
                for keyword in ["hood", "door", "bumper", "fender", "roof", "quarter",
                               "deck lid", "trunk", "liftgate", "tail gate", "headlamp",
                               "tail lamp", "radiator", "frame", "cowl", "pick up box",
                               "lift gate", "lift"]:
                    if keyword in desc:
                        repair_panels.add(keyword)
            
            # PDR context for hail
            if op == "pdr":
                for kw in ["hood", "roof", "fender", "door", "quarter", "deck", "trunk", "lift"]:
                    if kw in desc:
                        pdr_panels.add(kw)

        for line in all_lines:
            if line.get("is_header"):
                continue
            
            op_label = str(line.get("operation_label", "")).lower()
            desc = str(line.get("description", "")).lower()
            
            if op_label not in ("remove & install",):
                continue
            
            line_no = line.get("line_no", "?")
            
            # PDR context exceptions from prior rules
            if "insulator" in desc and "hood" in pdr_panels:
                continue
            if "headliner" in desc and "roof" in pdr_panels:
                if "drop" in desc:
                    results.append(RuleResult(
                        rule_id=self.rule_id, title="Headliner Drop — Write Full R&I",
                        category=self.category, severity="high",
                        affected_lines=[line_no],
                        summary=f"Headliner DROP L{line_no} — NatGen does not allow drop, write full R&I.",
                        why_flagged="NatGen: headliner drop is not permitted. Write for full R&I of headliner.",
                        recommended_actions="Change headliner DROP to full R&I. Do not use drop labor time.",
                    ))
                continue
            if "hood" in desc and "hood" in pdr_panels:
                continue
            if ("lift" in desc or "tail" in desc) and "gate" in desc and "lift" in pdr_panels:
                continue
            
            # Check MOTOR included rules
            # Check MOTOR included rules (REPLACE only)
            is_included = False
            matched_parent = ""
            
            for parent_kw, child_kw in MOTOR_INCLUDED:
                if child_kw in desc:
                    if parent_kw in replace_parents or parent_kw in pdr_panels:
                        is_included = True
                        matched_parent = parent_kw
                        break
            
            if is_included:
                continue
            
            # Hail claims: all trim, liner, lamp, molding R&I is for PDR access — skip
            if pdr_panels:
                continue
            
            # Check if any repair/PDR on this panel justifies R&I access
            any_justification = any(
                kw in desc for kw in repair_panels | pdr_panels | replace_parents
            )
            
            if any_justification:
                # R&I justified for repair/PDR/replace access — low flag
                confidence = 0.3
                sev = "low"
            else:
                confidence = 0.6
                sev = "medium"
            
            results.append(RuleResult(
                rule_id=self.rule_id, title=self.title,
                category=self.category, severity=sev, confidence=confidence,
                affected_lines=[line_no],
                summary=f"R&I L{line_no}: {line.get('description','')[:50]} — verify per MOTOR included ops.",
                why_flagged=(
                    f"Per MOTOR P-pages, R&I of this item may be included in a parent operation. "
                    f"If a related repair/replace/PDR exists on this panel, the R&I is already covered. "
                    + (f"Matched parent: {matched_parent}" if matched_parent else "No matching parent found.")
                ),
                recommended_actions=(
                    f"Check MOTOR P-pages for included operations on this panel. "
                    f"If R&I is included in a parent op, remove the separate charge. "
                    f"If R&I is genuinely required for access, document justification."
                ),
                debug_context={"matched_parent": matched_parent, "confidence": confidence},
            ))
        
        return results
