"""
Shared audit presentation utilities.
Extracted from duplicated logic in api/main.py QC endpoint and api/full_audit.py.
"""
from collections import defaultdict
from typing import List, Dict, Any


# Confidence scores per rule type
CONFIDENCE: Dict[str, float] = {
    # Deterministic rules — high confidence
    "NATGEN_014": 1.0, "AUDIT_007": 1.0, "AUDIT_008": 0.9, "AUDIT_004": 0.85,
    "NATGEN_002": 0.9, "NATGEN_004": 0.9, "NATGEN_013": 1.0, "NATGEN_020": 0.9,
    "STATE_002": 1.0, "STATE_003": 1.0,
    # Medium confidence — pattern-based
    "NATGEN_006": 0.7, "NATGEN_008": 0.6, "NATGEN_012": 0.7, "NATGEN_001": 0.75,
    "HAIL_001": 0.65, "SUPP_001": 0.7, "PAINT_001": 0.8, "FRAME_001": 0.8,
    "ALIGN_001": 0.7, "AUDIT_010": 0.6, "AUDIT_006": 0.7,
    # Lower confidence — heuristic
    "PHOTO_VERIFY": 0.5, "LEARN_001": 0.5,
}


def get_confidence(rule_id: str) -> float:
    """Return confidence score for a given rule_id, defaulting to 0.7."""
    return CONFIDENCE.get(rule_id, 0.7)


def group_findings(findings: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Group findings by their recommended action category.

    Returns a dict with keys: state, remove, fix, verify, attach, review.
    """
    groups = defaultdict(list)
    for f in findings:
        rid = f.get("rule_id", "")
        if rid.startswith("STATE_"):
            groups["state"].append(f)
        elif rid in ("NATGEN_014", "AUDIT_007"):
            groups["remove"].append(f)
        elif rid in ("NATGEN_002", "NATGEN_001", "NATGEN_011", "NATGEN_004"):
            groups["fix"].append(f)
        elif rid in ("NATGEN_006", "NATGEN_008", "HAIL_001", "SUPP_001",
                     "SUPP_002", "SUPP_003", "SUPP_004", "SUPP_005",
                     "AUDIT_010", "AUDIT_004", "NATGEN_012",
                     "PAINT_001", "FRAME_001", "ALIGN_001", "MOTOR_001", "RATE_001"):
            groups["verify"].append(f)
        elif rid == "CHECK_005":
            groups["fix"].append(f)
        elif rid.startswith("CHECK_"):
            groups["attach"].append(f)
        elif rid == "TL_001":
            groups["review"].append(f)
        else:
            groups["review"].append(f)
    return dict(groups)


def build_passed(parsed_data: dict, shop: dict, is_supplement: bool) -> list:
    """Build passed items — things checked that passed."""
    passed = []
    if shop.get("name"):
        name_lower = shop["name"].lower()
        if any(kw in name_lower for kw in ("shop of choice", "owner's choice", "owners choice")):
            passed.append("Shop of choice — no action needed")
    if is_supplement and shop.get("name") and shop.get("address"):
        passed.append("Supplement shop info verified")
    # PDR context — detect what was skipped
    for panel_name, checks in [
        ("HOOD", ["hood assy", "insulator"]),
        ("ROOF", ["headliner"]),
        ("LIFTGATE", ["liftgate"]),
    ]:
        has_pdr = any(
            str(r.get("operation_label", "")).lower() == "pdr" and panel_name.lower() in str(r.get("description", "")).lower()
            for p in parsed_data.get("claim", {}).get("panels", [])
            for r in p.get("rows", [])
        )
        if has_pdr:
            for check in checks:
                passed.append(f"{panel_name.title()} PDR detected — R&I {check} not flagged")
    return passed


def build_findings_dict(
    groups: Dict[str, List[Dict[str, Any]]],
    confidence_map: Dict[str, float] = None,
) -> Dict[str, List[Dict[str, Any]]]:
    """Build the structured findings dict grouped by category with confidence attached."""
    if confidence_map is None:
        confidence_map = CONFIDENCE
    result = {}
    for cat in ["state", "remove", "fix", "verify", "attach", "review"]:
        items = groups.get(cat, [])
        result[cat] = [
            {
                "severity": f.get("severity"),
                "summary": f.get("summary"),
                "lines": f.get("affected_lines", []),
                "confidence": confidence_map.get(f.get("rule_id", ""), 0.7),
            }
            for f in items
        ]
    return result
