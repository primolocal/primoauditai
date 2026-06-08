"""MOTOR Guide P-Page Rules — included/not-included operations per MOTOR standards.
"""
from __future__ import annotations

from src.engine.base import BaseRule, RuleResult
from src.engine.context import AuditContext


# MOTOR included operations: when PARENT operation is performed, CHILD R&I is INCLUDED
MOTOR_INCLUDED = [
    ("hood", "insulator"), ("hood", "hinge"),
    ("cowl", "cowl grille"), ("cowl", "wiper arm"), ("cowl", "wiper motor"),
    ("door", "belt molding"), ("door", "weatherstrip"), ("door", "mirror"),
    ("door", "handle"), ("door", "lock"), ("door", "latch"),
    ("door", "regulator"), ("door", "trim panel"), ("door", "door glass"),
    ("door", "run channel"),
    ("bumper", "bracket"), ("bumper", "reinforcement"),
    ("bumper", "absorber"), ("bumper", "impact bar"),
    ("fender", "liner"), ("fender", "splash shield"),
    ("roof", "headliner"), ("roof", "sunroof"),
    ("roof", "roof rack"), ("roof", "antenna"),
    ("liftgate", "trim panel"), ("liftgate", "glass"),
    ("liftgate", "wiper"), ("liftgate", "handle"),
    ("liftgate", "molding"), ("liftgate", "emblem"), ("liftgate", "nameplate"),
    ("tail gate", "trim panel"), ("tail gate", "handle"),
    ("quarter", "trim panel"), ("quarter", "glass"), ("quarter", "molding"),
    ("headlamp", "bracket"), ("headlamp", "mounting panel"),
    ("tail lamp", "bracket"),
    ("deck lid", "trim panel"), ("deck lid", "lock"),
    ("deck lid", "emblem"), ("deck lid", "nameplate"), ("deck lid", "spoiler"),
    ("trunk", "trim panel"), ("trunk", "carpet"),
    ("pick up box", "wheelhouse liner"), ("pick up box", "molding"), ("pick up box", "tie down"),
    ("radiator", "condenser"), ("radiator", "fan"),
    ("frame", "crossmember"), ("frame", "body mount"),
]


class MOTORIncludedRIRule(BaseRule):
    """MOTOR_001: Smart R&I check using MOTOR P-page knowledge."""
    rule_id = "MOTOR_001"
    category = "line_item_support"
    description = "R&I may be included in parent operation per MOTOR P-pages"
    severity = "low"

    def applies(self, ctx: AuditContext) -> bool:
        return True

    def evaluate(self, ctx: AuditContext) -> list[RuleResult]:
        results = []
        all_lines = ctx.get_all_lines()

        # Build sets of parent operations by type
        replace_parents = set()
        repair_panels = set()
        pdr_panels = set()

        for line in all_lines:
            desc = str(line.get("description", "")).lower()
            op = str(line.get("operation_label", "")).lower()
            if op == "replace":
                for kw in ["hood", "door", "bumper", "fender", "roof", "quarter",
                           "deck lid", "trunk", "liftgate", "tail gate", "headlamp",
                           "tail lamp", "radiator", "frame", "cowl", "pick up box",
                           "lift gate", "lift"]:
                    if kw in desc:
                        replace_parents.add(kw)
            if op in ("repair", "pdr", "overhaul"):
                for kw in ["hood", "door", "bumper", "fender", "roof", "quarter",
                           "deck lid", "trunk", "liftgate", "tail gate", "headlamp",
                           "tail lamp", "radiator", "frame", "cowl", "pick up box",
                           "lift gate", "lift"]:
                    if kw in desc:
                        repair_panels.add(kw)
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
            line_no = line.get("line_no", 0) or 0

            # PDR context exceptions
            if "insulator" in desc and "hood" in pdr_panels:
                continue
            if "headliner" in desc and "roof" in pdr_panels:
                if "drop" in desc:
                    results.append(RuleResult(
                        rule_id=self.rule_id,
                        category=self.category,
                        severity="high",
                        description=f"Headliner DROP L{line_no} — NatGen does not allow drop, write full R&I.",
                        line_numbers=[line_no],
                        summary=f"Headliner DROP L{line_no} — write full R&I per NatGen.",
                        detail="NatGen: headliner drop is not permitted. Write full R&I of headliner.",
                        action="Change headliner DROP to full R&I. Do not use drop labor time.",
                    ))
                continue
            if "hood" in desc and "hood" in pdr_panels:
                continue
            if ("lift" in desc or "tail" in desc) and "gate" in desc and "lift" in pdr_panels:
                continue

            # Check MOTOR included rules
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

            any_justification = any(kw in desc for kw in repair_panels | pdr_panels | replace_parents)
            if any_justification:
                sev = "low"
                conf = 0.3
            else:
                sev = "medium"
                conf = 0.6

            results.append(RuleResult(
                rule_id=self.rule_id,
                category=self.category,
                severity=sev,
                description=f"R&I L{line_no}: {line.get('description','')[:50]} — verify per MOTOR included ops.",
                line_numbers=[line_no],
                confidence=conf,
                summary=f"R&I L{line_no}: verify per MOTOR P-page included operations.",
                detail=(
                    f"Per MOTOR P-pages, R&I of this item may be included in a parent operation. "
                    f"{'Matched parent: ' + matched_parent if matched_parent else 'No matching parent found.'}"
                ),
                action=(
                    "Check MOTOR P-pages for included operations. "
                    "If R&I is included in a parent op, remove separate charge. "
                    "If genuinely required for access, document justification."
                ),
            ))

        return results
