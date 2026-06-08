"""
QC Rules Engine - Validates estimate + photo packets for quality control.
Categories:
  PHOTOCOV: Photo coverage completeness
  COMPLETE: Estimate completeness (deductible, shop info, etc.)
  STATEQC:  State compliance (thresholds, rates, ZIPs)
  EXCEP:    Exception verification (supplements, A/M, LKQ transfers)
"""

import re
from typing import Any


class QCFinding:
    """A single QC finding dict — matches DB model structure."""
    def __init__(
        self,
        rule_id: str,
        category: str,
        severity: str,
        description: str,
        line_numbers: list[int] = None,
        applies: bool = True,
        suggested_fix: str = None,
    ):
        self.rule_id = rule_id
        self.category = category
        self.severity = severity
        self.description = description
        self.line_numbers = line_numbers or []
        self.applies = applies
        self.suggested_fix = suggested_fix

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "category": self.category,
            "severity": self.severity,
            "description": self.description,
            "line_numbers": self.line_numbers,
            "confidence": 1.0,
            "applies": self.applies,
            "suggested_fix": self.suggested_fix,
        }


def run_qc_rules(
    parsed_lines: list[dict[str, Any]],
    parsed_metadata: dict[str, Any],
    photos: list[dict[str, Any]],
    vin_present: bool = False,
    odo_present: bool = False,
    damage_present: bool = False,
    is_supplement: bool = False,
) -> list[dict[str, Any]]:
    """Run all QC rules against a parsed estimate + extracted photos."""
    findings: list[QCFinding] = []

    # ── Photo Coverage (only if checkboxes not already checked) ──
    if not (vin_present and odo_present and damage_present):
        findings.extend(_check_photo_coverage(photos, parsed_lines, parsed_metadata, vin_present, odo_present, damage_present))

    # ── Estimate Completeness ──
    findings.extend(_check_estimate_completeness(parsed_lines, parsed_metadata))

    # ── State Compliance ──
    findings.extend(_check_state_compliance(parsed_lines, parsed_metadata))

    # ── Exception Verification (suppressed for supplements — flags/manual entries expected) ──
    if not is_supplement:
        findings.extend(_check_exceptions(parsed_lines, parsed_metadata))

    return [f.to_dict() for f in findings if f.applies]


# ═══════════════════════════════════════════════════════════════════════
# PHOTO COVERAGE
# ═══════════════════════════════════════════════════════════════════════

def _check_photo_coverage(
    photos: list[dict[str, Any]],
    parsed_lines: list[dict[str, Any]],
    meta: dict[str, Any],
    vin_present: bool = False,
    odo_present: bool = False,
    damage_present: bool = False,
) -> list[QCFinding]:
    findings: list[QCFinding] = []
    photo_types = {p.get("photo_type", "") for p in photos}

    # VIN photo
    if not vin_present and "vin" not in photo_types:
        findings.append(
            QCFinding(
                rule_id="PHOTOCOV_001",
                category="photo_coverage",
                severity="high",
                description="VIN photo required but not found in packet",
                suggested_fix="Upload VIN plate photo",
            )
        )

    # Odometer photo
    if not odo_present and "odometer" not in photo_types:
        findings.append(
            QCFinding(
                rule_id="PHOTOCOV_002",
                category="photo_coverage",
                severity="high",
                description="Odometer/mileage photo required but not found",
                suggested_fix="Upload dashboard photo showing mileage",
            )
        )

    # Damage photos: compare Replace operations to damage photos
    if not damage_present and "damage" not in photo_types:
        replace_panels = set()
        for line in parsed_lines:
            if line.get("operation") == "Repl":
                ln = line.get("line_no", "")
                if ln and ((isinstance(ln, str) and ln.isdigit()) or (isinstance(ln, int) and ln > 0)):
                    panel = line.get("panel_name", "Unknown")
                    replace_panels.add(panel)
        if replace_panels:
            findings.append(
                QCFinding(
                    rule_id="PHOTOCOV_003",
                    category="photo_coverage",
                    severity="high",
                    description=f"Replace operations found ({len(replace_panels)} panels) but no damage photos",
                    suggested_fix="Upload photos of damaged panels listed in estimate",
                )
            )

    # Damage to non-replaced panels (needs documentation)
    if damage_present:
        body_panels = set()
        for line in parsed_lines:
            op = line.get("operation", "")
            if op in ("Rpr", "R&I", "Repl"):
                panel = line.get("panel_name", "")
                if panel:
                    body_panels.add(panel)
        if not body_panels:
            findings.append(
                QCFinding(
                    rule_id="PHOTOCOV_004",
                    category="photo_coverage",
                    severity="low",
                    description="No body/paint operations found — verify damage photos show all impact areas",
                )
            )

    return findings


# ═══════════════════════════════════════════════════════════════════════
# ESTIMATE COMPLETENESS
# ═══════════════════════════════════════════════════════════════════════

def _check_estimate_completeness(
    parsed_lines: list[dict[str, Any]], meta: dict[str, Any]
) -> list[QCFinding]:
    findings: list[QCFinding] = []

    # Deductible (must be listed on estimate)
    if not meta.get("deductible"):
        findings.append(
            QCFinding(
                rule_id="COMPLETE_001",
                category="completeness",
                severity="medium",
                description="Deductible amount not found on estimate",
                suggested_fix="Verify deductible is listed on estimate or in notes",
            )
        )

    # Shop information
    if not meta.get("shop_name"):
        findings.append(
            QCFinding(
                rule_id="COMPLETE_002",
                category="completeness",
                severity="high",
                description="Shop name missing from estimate header",
                suggested_fix="Verify repair facility name is present",
            )
        )

    if not meta.get("shop_address"):
        findings.append(
            QCFinding(
                rule_id="COMPLETE_003",
                category="completeness",
                severity="medium",
                description="Shop address missing from estimate",
                suggested_fix="Verify repair facility address is present",
            )
        )

    # Insurance (use any of these keys: insurance_company, insurer, carrier)
    insurance = meta.get("insurance_company") or meta.get("insurer") or meta.get("carrier")
    if not insurance:
        findings.append(
            QCFinding(
                rule_id="COMPLETE_004",
                category="completeness",
                severity="high",
                description="Insurance company not listed on estimate",
                suggested_fix="Verify insurance company name is present",
            )
        )

    # License plate (may not be on all estimates — low severity)
    if not meta.get("license_plate"):
        findings.append(
            QCFinding(
                rule_id="COMPLETE_005",
                category="completeness",
                severity="medium",
                description="License plate not recorded on estimate",
                suggested_fix="Verify license plate is present in vehicle section",
            )
        )

    # Odometer has a separate key
    if not meta.get("odometer"):
        findings.append(
            QCFinding(
                rule_id="COMPLETE_006",
                category="completeness",
                severity="low",
                description="Odometer not recorded on estimate",
                suggested_fix="Verify mileage is present in vehicle section",
            )
        )

    # License plate
    if not meta.get("license_plate"):
        findings.append(
            QCFinding(
                rule_id="COMPLETE_005",
                category="completeness",
                severity="medium",
                description="License plate not recorded on estimate",
                suggested_fix="Verify license plate is present in vehicle section",
            )
        )

    # Odometer on estimate
    if meta.get("odometer") is None:
        findings.append(
            QCFinding(
                rule_id="COMPLETE_006",
                category="completeness",
                severity="medium",
                description="Odometer not recorded on estimate",
                suggested_fix="Verify odometer reading is present",
            )
        )

    # Repair Facility rules (differs for original vs supplement)
    shop_name = meta.get("shop_name")
    shop_address = meta.get("shop_address")
    shop_choice = meta.get("shop_of_choice", False)
    is_supp = meta.get("is_supplement", False)

    if is_supp:
        # Supplements: full shop name + address required. Shop of Choice NOT acceptable
        if not shop_name or not shop_address:
            findings.append(
                QCFinding(
                    rule_id="COMPLETE_007",
                    category="completeness",
                    severity="high",
                    description="Repair facility not fully listed on supplement — shop name and address required",
                    suggested_fix="Repair facility with name and address must be listed on all supplements",
                )
            )
        if shop_choice:
            findings.append(
                QCFinding(
                    rule_id="COMPLETE_008",
                    category="completeness",
                    severity="high",
                    description="Shop of Choice not acceptable on supplement — full shop info required",
                    suggested_fix="Replace Shop of Choice with actual repair facility name and address",
                )
            )
    else:
        # Original estimate: shop info OR Shop of Choice required
        if not shop_name:
            findings.append(
                QCFinding(
                    rule_id="COMPLETE_007",
                    category="completeness",
                    severity="high",
                    description="No repair facility listed — shop name or Shop of Choice required",
                    suggested_fix="Repair facility must be identified, or Shop of Choice/Owner's Choice designated",
                )
            )
        elif not shop_address and not shop_choice:
            findings.append(
                QCFinding(
                    rule_id="COMPLETE_007",
                    category="completeness",
                    severity="high",
                    description="Repair facility listed but no address provided",
                    suggested_fix="Repair facility address must be included on estimate",
                )
            )

    return findings


# ═══════════════════════════════════════════════════════════════════════
# STATE COMPLIANCE
# ═══════════════════════════════════════════════════════════════════════

def _check_state_compliance(
    parsed_lines: list[dict[str, Any]], meta: dict[str, Any]
) -> list[QCFinding]:
    findings: list[QCFinding] = []
    state = meta.get("state") or meta.get("vehicle_state") or meta.get("shop_state_derived") or ""
    zip_code = meta.get("zip_code") or meta.get("shop_zip") or ""

    if not state:
        findings.append(
            QCFinding(
                rule_id="STATEQC_001",
                category="state_compliance",
                severity="high",
                description="State not indicated on estimate",
                suggested_fix="Verify state is present in vehicle/insured section",
            )
        )

    # ZIP code check suppressed — not a rejection trigger

    # Total loss threshold check for TX (80%)
    if state and state.upper() == "TX":
        total = meta.get("total_estimate", 0) or 0
        acv = meta.get("acv", 0) or 0
        if acv and total and total >= 0.8 * acv:
            findings.append(
                QCFinding(
                    rule_id="STATEQC_003",
                    category="state_compliance",
                    severity="critical",
                    description=f"Estimate exceeds TX total loss threshold ({(total/acv):.0%} of ACV)",
                    suggested_fix="Flag for total loss review or obtain NADA valuation",
                )
            )

    return findings


# ═══════════════════════════════════════════════════════════════════════
# EXCEPTION VERIFICATION
# ═══════════════════════════════════════════════════════════════════════

def _check_exceptions(
    parsed_lines: list[dict[str, Any]], meta: dict[str, Any]
) -> list[QCFinding]:
    findings: list[QCFinding] = []

    # Supplement flags (** + S01/S02)
    supp_lines = [l for l in parsed_lines if l.get("flag") == "**" or l.get("supplement")]
    if supp_lines:
        findings.append(
            QCFinding(
                rule_id="EXCEP_001",
                category="exception",
                severity="medium",
                description=f"Supplement flags found on {len(supp_lines)} line(s) — verify documentation",
                line_numbers=[int(l["line_no"]) for l in supp_lines if l["line_no"].isdigit()],
                suggested_fix="Ensure prior supplement documentation is attached",
            )
        )

    # Manual entries (# flag)
    manual_lines = [l for l in parsed_lines if l.get("flag") == "#"]
    if manual_lines:
        findings.append(
            QCFinding(
                rule_id="EXCEP_002",
                category="exception",
                severity="medium",
                description=f"Manual entry (#) found on {len(manual_lines)} line(s) — verify justification",
                line_numbers=[int(l["line_no"]) for l in manual_lines if l["line_no"].isdigit()],
                suggested_fix="Ensure justification is documented for each manual entry",
            )
        )

    # A/M parts without justification
    am_lines = [l for l in parsed_lines if l.get("part_type") in {"A/M", "AF"}]
    if am_lines:
        findings.append(
            QCFinding(
                rule_id="EXCEP_003",
                category="exception",
                severity="medium",
                description=f"Aftermarket (A/M) parts on {len(am_lines)} line(s) — verify shop justification",
                line_numbers=[int(l["line_no"]) for l in am_lines if l["line_no"].isdigit()],
                suggested_fix="Verify shop provided justification for aftermarket part selection",
            )
        )

    # LKQ parts — transfer lines
    lkq_lines = [l for l in parsed_lines if l.get("part_type") in {"LKQ", "REC", "USED"}]
    if lkq_lines:
        findings.append(
            QCFinding(
                rule_id="EXCEP_004",
                category="exception",
                severity="medium",
                description=f"LKQ/Used/Recycled parts on {len(lkq_lines)} line(s) — verify transfer operations",
                line_numbers=[int(l["line_no"]) for l in lkq_lines if l["line_no"].isdigit()],
                suggested_fix="Verify transfer lines are present for LKQ/Used part assemblies",
            )
        )

    return findings
