"""
QC Scorer — calculates carrier confidence score and generates rejection reasons.
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class QCScoreResult:
    total_score: int
    max_score: int
    ready_for_carrier: bool
    score_breakdown: dict[str, int]
    rejection_reasons: list[str]
    auditor_note: str


def calculate_carrier_confidence(
    findings: list[dict[str, Any]],
    photo_counts: dict[str, int],
    metadata: dict[str, Any],
) -> QCScoreResult:
    """Score an estimate+photo packet for carrier readiness.
    
    Categories (25 pts each):
      - Photo Coverage (VIN, odometer, damage)
      - Estimate Completeness (deductible, shop, insurance, license, odometer)
      - State Compliance (state, ZIP, threshold check)
      - Exception Handling (supplements, manual entries, A/M, LKQ)
      
    Pass threshold: 70/100
    """
    
    score_breakdown: dict[str, int] = {}
    rejection_reasons: list[str] = []
    
    findings_by_cat: dict[str, list[dict[str, Any]]] = {
        "photo_coverage": [],
        "completeness": [],
        "state_compliance": [],
        "exception": [],
    }
    for f in findings:
        cat = f.get("category", "")
        if cat in findings_by_cat:
            findings_by_cat[cat].append(f)
    
    # ════════════════════ Photo Coverage (25 pts) ════════════════════
    auto_reject = False
    photo_score = 25
    photo_fails: list[str] = []
    
    if photo_counts.get("photo_vin", 0) == 0:
        photo_score -= 25
        auto_reject = True
        photo_fails.append("AUTO-REJECT: VIN photo missing from packet")
    if photo_counts.get("photo_odometer", 0) == 0:
        photo_score -= 25
        auto_reject = True
        photo_fails.append("AUTO-REJECT: Odometer photo missing from packet")
    if photo_counts.get("photo_damage", 0) == 0:
        photo_score -= 25
        auto_reject = True
        photo_fails.append("AUTO-REJECT: Damage photos missing from packet")
    
    photo_score = max(photo_score, 0)
    score_breakdown["photo_coverage"] = photo_score
    rejection_reasons.extend(photo_fails)
    
    # ════════════════════ Estimate Completeness (25 pts) ════════════════════
    complete_score = 25
    complete_fails: list[str] = []
    
    if not metadata.get("deductible"):
        complete_score -= 5
        complete_fails.append("Deductible not specified")
    if not metadata.get("shop_name"):
        complete_score -= 5
        complete_fails.append("Shop name missing")
    if not metadata.get("shop_address"):
        complete_score -= 5
        complete_fails.append("Shop address missing")
    # Insurance — try multiple keys
    insurance = metadata.get("insurance_company") or metadata.get("insurer") or metadata.get("carrier")
    if not insurance:
        complete_score -= 5
        complete_fails.append("Insurance company not listed")
    if not metadata.get("license_plate"):
        complete_score -= 3
        complete_fails.append("License plate not recorded")
    if not metadata.get("odometer"):
        complete_score -= 2
        complete_fails.append("Odometer missing from estimate")
    
    complete_score = max(complete_score, 0)
    score_breakdown["estimate_completeness"] = complete_score
    rejection_reasons.extend(complete_fails)
    
    # ════════════════════ State Compliance (25 pts) ════════════════════
    state_score = 25
    state_fails: list[str] = []
    
    for f in findings_by_cat["state_compliance"]:
        rid = f.get("rule_id", "")
        if rid == "STATEQC_001":
            state_score -= 8
            state_fails.append("State not indicated on estimate")
        elif rid == "STATEQC_002":
            state_score -= 8
            state_fails.append("ZIP code missing from estimate")
        elif rid == "STATEQC_003":
            state_score -= 9  # Total loss — critical
            state_fails.append("Estimate exceeds state total loss threshold")
        else:
            state_score -= 5
            state_fails.append(f.get("description", "State compliance issue"))
    
    state_score = max(state_score, 0)
    score_breakdown["state_compliance"] = state_score
    rejection_reasons.extend(state_fails)
    
    # ════════════════════ Exception Handling (25 pts) ════════════════════
    exception_score = 25
    exception_fails: list[str] = []
    
    for f in findings_by_cat["exception"]:
        rid = f.get("rule_id", "")
        desc = f.get("description", "")
        if rid == "EXCEP_001":
            exception_score -= 3
            exception_fails.append("Supplement flags present — verify documentation")
        elif rid == "EXCEP_002":
            exception_score -= 3
            exception_fails.append("Manual entries (#) present — verify justification")
        elif rid == "EXCEP_003":
            exception_score -= 8
            exception_fails.append("Aftermarket parts — verify shop justification")
        elif rid == "EXCEP_004":
            exception_score -= 5
            exception_fails.append("LKQ/Used parts — verify transfer operations")
        else:
            exception_score -= 3
            exception_fails.append(desc)
    
    exception_score = max(exception_score, 0)
    score_breakdown["exception_handling"] = exception_score
    rejection_reasons.extend(exception_fails)
    
    total = sum(score_breakdown.values())
    
    # Generate auto-auditor note
    auto_note = _generate_auditor_note(total, rejection_reasons)
    
    return QCScoreResult(
        total_score=total,
        max_score=100,
        ready_for_carrier=not auto_reject and total >= 70,
        score_breakdown=score_breakdown,
        rejection_reasons=rejection_reasons,
        auditor_note=auto_note,
    )


def _generate_auditor_note(score: int, rejections: list[str]) -> str:
    """Generate a default auditor note based on score."""
    if score >= 85:
        return "✓ All checks passed. Estimate is complete and compliant. Ready for carrier submission."
    elif score >= 70:
        return f"⚠ Conditional pass ({score}/100). Minor exceptions found: {len(rejections)} item(s). Review and address flagged items before submission."
    else:
        issues = "; ".join(rejections[:3])
        if len(rejections) > 3:
            issues += f" and {len(rejections) - 3} more"
        return f"✗ Not ready for carrier ({score}/100). Critical issues: {issues}. Correct before resubmitting."


def export_training_dataset(
    packet: dict[str, Any],
    findings: list[dict[str, Any]],
    score_result: QCScoreResult,
) -> dict[str, Any]:
    """Export a structured dataset sample for ML training.
    
    Returns a JSON-ready dict with fields for supervised learning:
      - inputs: packet metadata, photo counts, finding descriptions
      - labels: score, ready_for_carrier, rejection_reasons
    """
    metadata = packet.get("parsed_metadata", {})
    
    return {
        "packet_id": packet.get("id"),
        "timestamp": packet.get("created_at"),
        "inputs": {
            "vehicle_year": metadata.get("year"),
            "vehicle_make": metadata.get("make"),
            "vehicle_model": metadata.get("model"),
            "state": metadata.get("state"),
            "zip_code": metadata.get("zip_code"),
            "insurance_company": metadata.get("insurance_company"),
            "shop_name": metadata.get("shop_name"),
            "deductible": metadata.get("deductible"),
            "total_estimate": metadata.get("total_estimate"),
            "photo_vin": packet.get("photo_vin", 0),
            "photo_odometer": packet.get("photo_odometer", 0),
            "photo_damage": packet.get("photo_damage", 0),
            "photo_total": packet.get("photo_total", 0),
            "line_count": len(packet.get("parsed_lines", [])),
            "finding_count": len(findings),
            "findings": [
                {
                    "rule_id": f.get("rule_id"),
                    "category": f.get("category"),
                    "severity": f.get("severity"),
                    "description": f.get("description"),
                    "line_numbers": f.get("line_numbers", []),
                }
                for f in findings
            ],
        },
        "labels": {
            "carrier_confidence_score": score_result.total_score,
            "max_score": score_result.max_score,
            "ready_for_carrier": score_result.ready_for_carrier,
            "rejection_reasons": score_result.rejection_reasons,
            "score_breakdown": score_result.score_breakdown,
        },
        "auditor_note": score_result.auditor_note,
    }
