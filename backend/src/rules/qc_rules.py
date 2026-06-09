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

    # ── Tax & Labor Rate Verification ──
    findings.extend(_check_rates(parsed_lines, parsed_metadata))

    # ── Exception Verification (suppressed for supplements — flags/manual entries expected) ──
    if not is_supplement:
        findings.extend(_check_exceptions(parsed_lines, parsed_metadata))
    else:
        # Supplements: only check A/M justification, not flags/manual entries
        findings.extend(_check_exceptions_supplement(parsed_lines, parsed_metadata))

    # ── Line Item Analysis ──
    findings.extend(_check_line_items(parsed_lines, parsed_metadata))

    # ── Financial Analysis ──
    findings.extend(_check_financials(parsed_lines, parsed_metadata))

    # ── Vehicle Info ──
    findings.extend(_check_vehicle_completeness(parsed_lines, parsed_metadata))

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

    # Shop info is covered by COMPLETE_007 — suppress individual name/address checks

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
                    description="Repair Facility/Shop of Choice is missing — name and address required on supplements",
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
                    description="Repair Facility/Shop of Choice is missing",
                    suggested_fix="Repair facility must be identified, or Shop of Choice/Owner's Choice designated",
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

    # LKQ transfer check suppressed — audit function, not QC

    return findings
def _check_rates(
    parsed_lines: list[dict[str, Any]], meta: dict[str, Any]
) -> list[QCFinding]:
    """Verify tax rate and labor rate against reference data."""
    findings: list[QCFinding] = []
    
    from src.rules.reference_data import check_tax_rate, check_labor_rate

    state = meta.get("state") or meta.get("vehicle_state") or meta.get("shop_state_derived") or ""
    zip_code = meta.get("zip_code") or meta.get("shop_zip") or ""

    # ── Tax rate verification ──
    tax_rate = meta.get("estimate_tax_rate")
    if tax_rate is not None and state:
        result = check_tax_rate(float(tax_rate), state, zip_code)
        if result.get("matches") is False:
            findings.append(
                QCFinding(
                    rule_id="TAX_001",
                    category="state_compliance",
                    severity="high",
                    description=f"Tax rate mismatch: estimate {result['actual']:.4f}, expected {result['expected']:.4f}",
                    suggested_fix=f"Verify correct tax rate for {state} ZIP {zip_code}. Expected: {result['expected']:.4f}",
                )
            )

    # ── Labor rate verification ──
    # Get the labor rate from the first mechanical labor line
    labor_rate = None
    for line in parsed_lines:
        lh = line.get("labor_hours")
        lp = line.get("part_price", 0) or 0
        if lh and lh > 0 and lp > 0:
            # Labor rate = part_price / labor_hours for body labor
            # Actually, labor rate is per hour from the estimate header
            pass
    
    # Use metadata labor rate if available
    est_labor = meta.get("labor_rate") or meta.get("body_labor_rate")
    if est_labor and state:
        result = check_labor_rate(float(est_labor), state, zip_code)
        if result.get("within_range") is False:
            findings.append(
                QCFinding(
                    rule_id="LABOR_001",
                    category="state_compliance",
                    severity="high",
                    description=f"Labor rate ${result['estimate']:.2f}/hr exceeds prevailing rate ${result['prevailing']:.2f}/hr by {result['pct_diff']:.1f}% (max 15%)",
                    suggested_fix=f"Verify labor rate for {state} ZIP {zip_code}. Upper limit: ${result['upper_limit']:.2f}/hr",
                )
            )

    return findings
def _check_exceptions_supplement(
    parsed_lines: list[dict[str, Any]], meta: dict[str, Any]
) -> list[QCFinding]:
    """Supplement exception checks — A/M justification only, no flags/manual entries."""
    findings: list[QCFinding] = []

    # A/M parts justification (still relevant for supplements)
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

    return findings
# ═══════════════════════════════════════════════════════════════════════
# LINE ITEM ANALYSIS
# ═══════════════════════════════════════════════════════════════════════

def _check_line_items(
    parsed_lines: list[dict[str, Any]], meta: dict[str, Any]
) -> list[QCFinding]:
    findings: list[QCFinding] = []

    # ── Overlapping operations (same panel, same operation) ──
    panel_ops: dict[tuple[str, str], list[int]] = {}
    for line in parsed_lines:
        if line.get("is_header"):
            continue
        panel = (line.get("panel_name") or "").strip().lower()
        op = (line.get("operation") or "").strip().lower()
        ln = line.get("line_no")
        if panel and op and ln:
            key = (panel, op)
            panel_ops.setdefault(key, []).append(int(ln) if str(ln).isdigit() else 0)

    overlap_lines: list[int] = []
    for (panel, op), lns in panel_ops.items():
        if len(lns) > 1:
            overlap_lines.extend(lns)

    if overlap_lines:
        findings.append(
            QCFinding(
                rule_id="LINE_001",
                category="line_analysis",
                severity="medium",
                description=f"Potential overlapping operations: {len(overlap_lines)} line(s) with same panel + operation",
                line_numbers=overlap_lines,
                suggested_fix="Review duplicate/overlapping entries — remove or document justification",
            )
        )

    # ── Suspicious labor hours (hood replace <2h, door skin <3h, full respray <8h) ──
    body_minimums = {
        "hood": 2.0, "front bumper": 1.5, "rear bumper": 1.5,
        "fender": 1.0, "door": 2.0, "quarter panel": 3.0,
        "roof": 4.0, "trunk lid": 1.5, "deck lid": 1.5,
        "liftgate": 2.0, "headlamp": 0.5, "tail lamp": 0.3,
        "grille": 0.5, "radiator support": 1.5,
    }
    suspicious_lines: list[int] = []
    for line in parsed_lines:
        if line.get("is_header"):
            continue
        op = (line.get("operation") or "").strip()
        if op not in ("Repl", "Rpr", "R&I"):
            continue
        lh = line.get("labor_hours") or 0
        panel = (line.get("panel_name") or "").strip().lower()
        minimum = body_minimums.get(panel)
        if minimum and float(lh) < minimum * 0.5:  # less than 50% of expected
            ln = line.get("line_no")
            if ln and str(ln).isdigit():
                suspicious_lines.append(int(ln))

    if suspicious_lines:
        findings.append(
            QCFinding(
                rule_id="LINE_002",
                category="line_analysis",
                severity="low",
                description=f"Unusually low labor hours on {len(suspicious_lines)} line(s) — verify operation scope",
                line_numbers=suspicious_lines,
                suggested_fix="Verify labor hours are correct for the listed operation",
            )
        )

    # ── Paint: missing blend on adjacent panel ──
    adjacents = [
        ("hood", "fender"), ("fender", "door"), ("door", "quarter panel"),
        ("quarter panel", "roof"), ("roof", "hood"),
        ("front bumper", "hood"), ("front bumper", "fender"),
        ("rear bumper", "quarter panel"), ("rear bumper", "trunk lid"),
        ("trunk lid", "quarter panel"), ("liftgate", "quarter panel"),
    ]
    painted_panels = set()
    all_panels = set()
    for line in parsed_lines:
        panel = (line.get("panel_name") or "").strip().lower()
        if not panel:
            continue
        all_panels.add(panel)
        paint_hours = line.get("paint_hours") or 0
        op = (line.get("operation") or "").strip()
        if float(paint_hours) > 0 or op in ("Repl", "Rpr"):
            painted_panels.add(panel)

    missing_blend: list[int] = []
    for a, b in adjacents:
        if a in painted_panels and b in all_panels and b not in painted_panels:
            for line in parsed_lines:
                ln = line.get("line_no")
                if (line.get("panel_name") or "").strip().lower() == a:
                    if ln and str(ln).isdigit():
                        missing_blend.append(int(ln))
                        break

    if missing_blend:
        findings.append(
            QCFinding(
                rule_id="LINE_003",
                category="line_analysis",
                severity="low",
                description=f"Paint operation on panel with adjacent panel not blended — verify if blend needed",
                line_numbers=missing_blend,
                suggested_fix="Check adjacent panel for required blend/clear coat",
            )
        )

    # ── LKQ parts without ACV carry‑over notation ──
    lkq_lines: list[int] = []
    for line in parsed_lines:
        pt = (line.get("part_type") or "").strip().upper()
        if pt in ("LKQ", "USED", "REC", "REM"):
            ln = line.get("line_no")
            if ln and str(ln).isdigit():
                lkq_lines.append(int(ln))

    if lkq_lines:
        findings.append(
            QCFinding(
                rule_id="LINE_004",
                category="line_analysis",
                severity="low",
                description=f"LKQ/used parts on {len(lkq_lines)} line(s) — verify part age and warranty notation",
                line_numbers=lkq_lines,
                suggested_fix="Document LKQ part mileage, age, and warranty terms",
            )
        )

    return findings


# ═══════════════════════════════════════════════════════════════════════
# FINANCIAL ANALYSIS
# ═══════════════════════════════════════════════════════════════════════

def _check_financials(
    parsed_lines: list[dict[str, Any]], meta: dict[str, Any]
) -> list[QCFinding]:
    findings: list[QCFinding] = []

    # ── Paint material % vs paint labor ──
    total_paint_labor = 0.0
    total_paint_material = 0.0
    for line in parsed_lines:
        ph = float(line.get("paint_hours") or 0)
        if ph > 0:
            total_paint_labor += ph
        pm = float(line.get("part_price") or 0) if "paint" in (line.get("description") or "").lower() else 0
        total_paint_material += pm

    if total_paint_labor > 0 and total_paint_material == 0:
        findings.append(
            QCFinding(
                rule_id="FIN_001",
                category="financial",
                severity="medium",
                description=f"Paint labor ({total_paint_labor:.1f} hrs) present but no paint materials found — verify materials are itemized",
                suggested_fix="Add paint material line item (typically 30-35% of paint labor)",
            )
        )

    # ── Total estimate vs ACV (market value check) ──
    total = float(meta.get("total_estimate") or 0)
    acv = float(meta.get("acv") or 0)
    if acv > 0 and total > acv * 0.75:
        findings.append(
            QCFinding(
                rule_id="FIN_002",
                category="financial",
                severity="high" if total > acv * 0.90 else "medium",
                description=f"Estimate total (${total:,.0f}) is {total/acv:.0%} of ACV (${acv:,.0f}) — total loss potential",
                suggested_fix="Flag for total loss evaluation" if total > acv * 0.90 else "Monitor for supplement creep",
            )
        )

    return findings


# ═══════════════════════════════════════════════════════════════════════
# VEHICLE INFO
# ═══════════════════════════════════════════════════════════════════════

def _check_vehicle_completeness(
    parsed_lines: list[dict[str, Any]], meta: dict[str, Any]
) -> list[QCFinding]:
    findings: list[QCFinding] = []

    # VIN
    vin = meta.get("vin") or ""
    if not vin or len(str(vin)) < 11:
        findings.append(
            QCFinding(
                rule_id="COMPLETE_009",
                category="completeness",
                severity="high",
                description="Complete VIN not recorded on estimate",
                suggested_fix="Full 17-character VIN must be present on every estimate",
            )
        )

    # Year / Make / Model
    missing = []
    for field in ("year", "make", "model"):
        if not meta.get(field):
            missing.append(field)
    if missing:
        findings.append(
            QCFinding(
                rule_id="COMPLETE_010",
                category="completeness",
                severity="medium",
                description=f"Missing vehicle info: {', '.join(missing)}",
                suggested_fix="Complete vehicle year, make, and model required",
            )
        )

    return findings
