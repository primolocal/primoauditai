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
    findings.extend(_check_photo_depth(photos, parsed_lines, parsed_metadata))

    # ── Estimate Completeness ──
    findings.extend(_check_estimate_completeness(parsed_lines, parsed_metadata))
    findings.extend(_check_estimate_metadata(parsed_lines, parsed_metadata))

    # ── State Compliance ──
    findings.extend(_check_state_compliance(parsed_lines, parsed_metadata))

    # ── Tax & Labor Rate Verification ──
    findings.extend(_check_rates(parsed_lines, parsed_metadata))

    # ── Exception Verification (suppressed for supplements — flags/manual entries expected) ──
    if not is_supplement:
        findings.extend(_check_exceptions(parsed_lines, parsed_metadata))
    else:
        findings.extend(_check_exceptions_supplement(parsed_lines, parsed_metadata))
    findings.extend(_check_supplement_quality(parsed_lines, parsed_metadata, is_supplement))

    # ── Line Item Analysis ──
    findings.extend(_check_line_items(parsed_lines, parsed_metadata))

    # ── Financial Analysis ──
    findings.extend(_check_financials(parsed_lines, parsed_metadata))

    # ── Vehicle Info ──
    findings.extend(_check_vehicle_completeness(parsed_lines, parsed_metadata))

    # ── Parts Sourcing ──
    findings.extend(_check_part_sourcing(parsed_lines, parsed_metadata))

    # ── Labor Analysis ──
    findings.extend(_check_labor_analysis(parsed_lines, parsed_metadata))

    # ── Enhanced State Compliance ──
    findings.extend(_check_state_enhanced(parsed_lines, parsed_metadata))

    # ── Carrier-Specific (NatGen / IAnet) ──
    findings.extend(_check_carrier_rules(parsed_lines, parsed_metadata))

    # ── Tommy's Audit Brain ──
    findings.extend(_check_tommy_rules(parsed_lines, parsed_metadata))

    # ── MOTOR Guide P-Page Rules ──
    findings.extend(_check_motor_rules(parsed_lines, parsed_metadata))

    # ── Supplement Documentation ──
    findings.extend(_check_supplement_docs(parsed_lines, parsed_metadata))

    # ── Extended Carrier Rules ──
    findings.extend(_check_extended_rules(parsed_lines, parsed_metadata))

    # ── Correlation Rules (glass/bumper/suspension/emblem/markup) ──
    findings.extend(_check_correlation_rules(parsed_lines, parsed_metadata))

    # ── Final Batch: core audit rules from v1 ──
    findings.extend(_check_final_rules(parsed_lines, parsed_metadata))

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

# ═══════════════════════════════════════════════════════════════════════
# PHOTO DEPTH (additional photo rules beyond presence/absence)
# ═══════════════════════════════════════════════════════════════════════

def _check_photo_depth(
    photos: list[dict[str, Any]],
    parsed_lines: list[dict[str, Any]],
    meta: dict[str, Any],
) -> list[QCFinding]:
    findings: list[QCFinding] = []
    photo_types = {p.get("photo_type", "") for p in photos}
    photo_count = len(photos)

    # License plate photo
    if "license_plate" not in photo_types:
        findings.append(
            QCFinding(
                rule_id="PHOTOCOV_005",
                category="photo_coverage",
                severity="medium",
                description="License plate photo not found in packet",
                suggested_fix="Include license plate photo (rear plate minimum)",
            )
        )

    # Minimum photo count: 1 per body panel with operations
    line_panels = set()
    for line in parsed_lines:
        if line.get("is_header"):
            continue
        panel = (line.get("panel_name") or "").strip().lower()
        op = (line.get("operation") or "")
        if panel and op in ("Repl", "Rpr", "R&I"):
            line_panels.add(panel)
    
    if line_panels and photo_count < len(line_panels):
        findings.append(
            QCFinding(
                rule_id="PHOTOCOV_006",
                category="photo_coverage",
                severity="medium",
                description=f"Photo count ({photo_count}) below panel count ({len(line_panels)}) — may be missing photos",
                suggested_fix="Include at least one photo per damaged panel",
            )
        )

    # Overview/full-vehicle photo
    if "overview" not in photo_types:
        findings.append(
            QCFinding(
                rule_id="PHOTOCOV_007",
                category="photo_coverage",
                severity="low",
                description="No overview/full-vehicle photo found — include 4-corner or full-vehicle shots",
                suggested_fix="Include at least one overview photo showing full vehicle and all damage",
            )
        )

    return findings


# ═══════════════════════════════════════════════════════════════════════
# EXTENDED COMPLETENESS (metadata beyond basic fields)
# ═══════════════════════════════════════════════════════════════════════

def _check_estimate_metadata(
    parsed_lines: list[dict[str, Any]], meta: dict[str, Any]
) -> list[QCFinding]:
    findings: list[QCFinding] = []

    # Point of impact
    if not meta.get("point_of_impact"):
        findings.append(
            QCFinding(
                rule_id="COMPL_011",
                category="completeness",
                severity="medium",
                description="Point of impact not recorded on estimate",
                suggested_fix="Record point of impact (e.g., front, rear, left, right, rollover)",
            )
        )

    # Prior damage section
    if not meta.get("prior_damage"):
        findings.append(
            QCFinding(
                rule_id="COMPL_012",
                category="completeness",
                severity="low",
                description="Prior damage section empty — verify no pre-existing damage exists",
                suggested_fix="Document prior damage or explicitly note 'none'",
            )
        )

    # Production date
    if not meta.get("production_date"):
        findings.append(
            QCFinding(
                rule_id="COMPL_013",
                category="completeness",
                severity="low",
                description="Vehicle production date not on estimate",
                suggested_fix="Include vehicle build/production date for parts compatibility",
            )
        )

    return findings


# ═══════════════════════════════════════════════════════════════════════
# SUPPLEMENT QUALITY
# ═══════════════════════════════════════════════════════════════════════

def _check_supplement_quality(
    parsed_lines: list[dict[str, Any]], meta: dict[str, Any], is_supplement: bool
) -> list[QCFinding]:
    findings: list[QCFinding] = []

    if not is_supplement:
        return findings

    supp_num = meta.get("supplement_number") or 0
    try:
        supp_num = int(supp_num)
    except (ValueError, TypeError):
        supp_num = 0

    # More than 3 supplements is unusual
    if supp_num > 3:
        findings.append(
            QCFinding(
                rule_id="EXCEP_004",
                category="exception",
                severity="low",
                description=f"Supplement #{supp_num} detected — claim has {supp_num} supplements. Verify necessity",
                suggested_fix="Review supplement history for potential supplement creep or missed initial damage",
            )
        )

    return findings


# ═══════════════════════════════════════════════════════════════════════
# EXTENDED LINE ANALYSIS
# ═══════════════════════════════════════════════════════════════════════

def _check_line_items(
    parsed_lines: list[dict[str, Any]], meta: dict[str, Any]
) -> list[QCFinding]:
    findings: list[QCFinding] = []

    # ── Overlapping operations ──
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
    overlap_lines = [ln for lns in panel_ops.values() if len(lns) > 1 for ln in lns]
    if overlap_lines:
        findings.append(
            QCFinding(rule_id="LINE_001", category="line_analysis", severity="medium",
                description=f"Overlapping operations on {len(overlap_lines)//2} panel(s)",
                line_numbers=overlap_lines,
                suggested_fix="Remove duplicates or document justification"))

    # ── Suspicious labor hours ──
    body_minimums = {"hood": 2.0, "front bumper": 1.5, "rear bumper": 1.5, "fender": 1.0,
        "door": 2.0, "quarter panel": 3.0, "roof": 4.0, "trunk lid": 1.5, "deck lid": 1.5,
        "liftgate": 2.0, "headlamp": 0.5, "tail lamp": 0.3, "grille": 0.5, "radiator support": 1.5}
    suspicious_lines = []
    for line in parsed_lines:
        if line.get("is_header"): continue
        op = (line.get("operation") or "").strip()
        if op not in ("Repl", "Rpr", "R&I"): continue
        lh = float(line.get("labor_hours") or 0)
        panel = (line.get("panel_name") or "").strip().lower()
        minimum = body_minimums.get(panel)
        if minimum and lh < minimum * 0.5:
            ln = line.get("line_no")
            if ln and str(ln).isdigit(): suspicious_lines.append(int(ln))
    if suspicious_lines:
        findings.append(
            QCFinding(rule_id="LINE_002", category="line_analysis", severity="low",
                description=f"Unusually low labor hours on {len(suspicious_lines)} line(s)",
                line_numbers=suspicious_lines,
                suggested_fix="Verify labor hours match operation scope"))

    # ── Missing blend panel ──
    adjacents = [("hood","fender"),("fender","door"),("door","quarter panel"),
        ("quarter panel","roof"),("roof","hood"),("front bumper","hood"),
        ("front bumper","fender"),("rear bumper","quarter panel"),
        ("rear bumper","trunk lid"),("trunk lid","quarter panel"),("liftgate","quarter panel")]
    painted = set()
    all_panels = set()
    for line in parsed_lines:
        panel = (line.get("panel_name") or "").strip().lower()
        if not panel: continue
        all_panels.add(panel)
        ph = float(line.get("paint_hours") or 0)
        op = (line.get("operation") or "").strip()
        if ph > 0 or op in ("Repl","Rpr"): painted.add(panel)
    missing_blend = []
    for a, b in adjacents:
        if a in painted and b in all_panels and b not in painted:
            for line in parsed_lines:
                ln = line.get("line_no")
                if (line.get("panel_name") or "").strip().lower() == a:
                    if ln and str(ln).isdigit(): missing_blend.append(int(ln))
                    break
    if missing_blend:
        findings.append(
            QCFinding(rule_id="LINE_003", category="line_analysis", severity="low",
                description="Paint on panel with adjacent unpainted panel — verify blend need",
                line_numbers=missing_blend,
                suggested_fix="Check adjacent panel for required blend/clear coat"))

    # ── LKQ parts ──
    lkq_lines = []
    for line in parsed_lines:
        pt = (line.get("part_type") or "").strip().upper()
        if pt in ("LKQ","USED","REC","REM"):
            ln = line.get("line_no")
            if ln and str(ln).isdigit(): lkq_lines.append(int(ln))
    if lkq_lines:
        findings.append(
            QCFinding(rule_id="LINE_004", category="line_analysis", severity="low",
                description=f"LKQ/used parts on {len(lkq_lines)} line(s) — verify age/warranty",
                line_numbers=lkq_lines,
                suggested_fix="Document LKQ part mileage, age, and warranty terms"))

    # ── A/M parts without CAPA ──
    am_lines = []
    for line in parsed_lines:
        pt = (line.get("part_type") or "").strip().upper()
        if pt in ("A/M","AF"):
            desc = (line.get("description") or "").lower()
            if "capa" not in desc:
                ln = line.get("line_no")
                if ln and str(ln).isdigit(): am_lines.append(int(ln))
    if am_lines:
        findings.append(
            QCFinding(rule_id="LINE_005", category="line_analysis", severity="medium",
                description=f"Aftermarket parts without CAPA cert on {len(am_lines)} line(s)",
                line_numbers=am_lines,
                suggested_fix="Verify CAPA certification for A/M structural/visible parts"))

    return findings


# ═══════════════════════════════════════════════════════════════════════
# EXTENDED FINANCIAL ANALYSIS
# ═══════════════════════════════════════════════════════════════════════

def _check_financials(
    parsed_lines: list[dict[str, Any]], meta: dict[str, Any]
) -> list[QCFinding]:
    findings: list[QCFinding] = []

    # ── Paint materials ──
    total_paint_labor = 0.0
    total_paint_material = 0.0
    for line in parsed_lines:
        ph = float(line.get("paint_hours") or 0)
        if ph > 0: total_paint_labor += ph
        pm = float(line.get("part_price") or 0) if "paint" in (line.get("description") or "").lower() else 0
        total_paint_material += pm
    if total_paint_labor > 0 and total_paint_material == 0:
        findings.append(
            QCFinding(rule_id="FIN_001", category="financial", severity="medium",
                description=f"Paint labor ({total_paint_labor:.1f}h) but no material line item",
                suggested_fix="Add paint material line (~30-35% of labor)"))

    # ── Estimate vs ACV ──
    total = float(meta.get("total_estimate") or 0)
    acv = float(meta.get("acv") or 0)
    if acv > 0 and total > acv * 0.75:
        findings.append(
            QCFinding(rule_id="FIN_002", category="financial",
                severity="high" if total > acv * 0.90 else "medium",
                description=f"Estimate (${total:,.0f}) is {total/acv:.0%} of ACV (${acv:,.0f})",
                suggested_fix="Flag for total loss evaluation" if total > acv*0.90 else "Monitor for supplement creep"))

    # ── Paint material cap (38% max) ──
    paint_mat_pct = (total_paint_material / total_paint_labor) if total_paint_labor > 0 else 0
    if paint_mat_pct > 0.38:
        findings.append(
            QCFinding(rule_id="FIN_003", category="financial", severity="medium",
                description=f"Paint materials ({paint_mat_pct:.0%}) exceed 38% cap of paint labor",
                suggested_fix="Cap paint materials at 38% of paint labor hours or provide justification"))

    # ── Sublet charges without notation ──
    sublet_lines = []
    for line in parsed_lines:
        op = (line.get("operation") or "").strip()
        desc = (line.get("description") or "").lower()
        if op == "SUBLET" or "sublet" in desc or "sub" in op.lower():
            ln = line.get("line_no")
            if ln and str(ln).isdigit(): sublet_lines.append(int(ln))
    if sublet_lines:
        findings.append(
            QCFinding(rule_id="FIN_004", category="financial", severity="low",
                description=f"Sublet operations on {len(sublet_lines)} line(s) — verify invoice attached",
                line_numbers=sublet_lines,
                suggested_fix="Attach sublet invoice and document scope of work"))

    return findings


# ═══════════════════════════════════════════════════════════════════════
# PARTS SOURCING
# ═══════════════════════════════════════════════════════════════════════

def _check_part_sourcing(
    parsed_lines: list[dict[str, Any]], meta: dict[str, Any]
) -> list[QCFinding]:
    findings: list[QCFinding] = []

    # Structural panel names (safety-critical)
    structural_panels = {"frame rail", "radiator support", "core support", "apron",
        "upper rail", "lower rail", "inner quarter", "rocker panel", "b-pillar",
        "a-pillar", "cowl", "floor pan", "firewall", "rear body panel", "crossmember"}

    structural_am: list[int] = []
    oe_lines: list[int] = []
    lkq_no_warranty: list[int] = []

    for line in parsed_lines:
        if line.get("is_header"):
            continue
        pt = (line.get("part_type") or "").strip().upper()
        panel = (line.get("panel_name") or "").strip().lower()
        ln = line.get("line_no")
        ln_int = int(ln) if ln and str(ln).isdigit() else 0

        # Structural + A/M = dangerous
        if pt in ("A/M", "AF") and any(sp in panel for sp in structural_panels):
            structural_am.append(ln_int)

        # OE price flag (price > $2000 without justification)
        if pt in ("OE", "OEM") and float(line.get("part_price") or 0) > 2000:
            oe_lines.append(ln_int)

        # LKQ without warranty
        if pt in ("LKQ", "USED") and "warranty" not in (line.get("description") or "").lower():
            lkq_no_warranty.append(ln_int)

    if structural_am:
        findings.append(
            QCFinding(rule_id="PART_001", category="parts", severity="critical",
                description=f"A/M parts on structural/safety component(s) — potential safety risk",
                line_numbers=structural_am,
                suggested_fix="Replace A/M structural parts with OE. A/M not acceptable for safety-critical components"))

    if oe_lines:
        findings.append(
            QCFinding(rule_id="PART_002", category="parts", severity="medium",
                description=f"High-value OE parts (>$2,000) on {len(oe_lines)} line(s) — verify pricing",
                line_numbers=oe_lines,
                suggested_fix="Verify OE part pricing against list/MSRP"))

    if lkq_no_warranty:
        findings.append(
            QCFinding(rule_id="PART_003", category="parts", severity="low",
                description=f"LKQ/used parts without warranty notation on {len(lkq_no_warranty)} line(s)",
                line_numbers=lkq_no_warranty,
                suggested_fix="Document warranty terms for all LKQ/used parts"))

    return findings


# ═══════════════════════════════════════════════════════════════════════
# LABOR ANALYSIS
# ═══════════════════════════════════════════════════════════════════════

def _check_labor_analysis(
    parsed_lines: list[dict[str, Any]], meta: dict[str, Any]
) -> list[QCFinding]:
    findings: list[QCFinding] = []

    total_body_labor = 0.0
    total_paint_labor = 0.0
    zero_labor_repl: list[int] = []
    misc_charges: list[int] = []

    for line in parsed_lines:
        if line.get("is_header"):
            continue
        bhl = float(line.get("labor_hours") or 0)
        phl = float(line.get("paint_hours") or 0)
        total_body_labor += bhl
        total_paint_labor += phl

        op = (line.get("operation") or "").strip()
        ln = line.get("line_no")
        ln_int = int(ln) if ln and str(ln).isdigit() else 0

        # Zero labor on Replace
        if op == "Repl" and bhl == 0:
            zero_labor_repl.append(ln_int)

        # Misc/various charges
        desc = (line.get("description") or "").lower()
        if any(kw in desc for kw in ("misc", "various", "shop supplies", "hazmat", "miscellaneous")):
            misc_charges.append(ln_int)

    # Paint ratio check (paint hours > 3x body hours is suspicious)
    if total_body_labor > 0 and total_paint_labor > total_body_labor * 3:
        findings.append(
            QCFinding(rule_id="LABOR_001", category="labor", severity="medium",
                description=f"Paint hours ({total_paint_labor:.1f}) > 3× body hours ({total_body_labor:.1f}) — verify",
                suggested_fix="Verify paint labor is appropriate for damage extent"))

    if zero_labor_repl:
        findings.append(
            QCFinding(rule_id="LABOR_002", category="labor", severity="high",
                description=f"Zero labor hours on {len(zero_labor_repl)} Replace line(s) — verify",
                line_numbers=zero_labor_repl,
                suggested_fix="Replace operations must include labor hours"))

    if misc_charges:
        findings.append(
            QCFinding(rule_id="LABOR_003", category="labor", severity="low",
                description=f"Unitemized/miscellaneous charges on {len(misc_charges)} line(s)",
                line_numbers=misc_charges,
                suggested_fix="Itemize all charges — avoid 'misc' or 'shop supplies' catch-alls"))

    return findings


# ═══════════════════════════════════════════════════════════════════════
# ENHANCED STATE COMPLIANCE
# ═══════════════════════════════════════════════════════════════════════

def _check_state_enhanced(
    parsed_lines: list[dict[str, Any]], meta: dict[str, Any]
) -> list[QCFinding]:
    findings: list[QCFinding] = []
    state = (meta.get("state") or "").strip().upper()
    vin = (meta.get("vin") or "").strip()
    year_str = str(meta.get("year") or "").strip()

    # ── RI: OE parts required on vehicles < 30 months ──
    if state == "RI":
        try:
            veh_year = int(year_str)
            if veh_year >= 2023:  # ~30 months from current
                for line in parsed_lines:
                    pt = (line.get("part_type") or "").strip().upper()
                    if pt in ("A/M", "AF", "LKQ", "USED"):
                        ln = line.get("line_no")
                        findings.append(
                            QCFinding(rule_id="STATEQC_010", category="state_compliance", severity="critical",
                                description=f"RI law requires OE parts on vehicles < 30 months. Non-OE part found.",
                                line_numbers=[int(ln)] if ln and str(ln).isdigit() else [],
                                suggested_fix="Replace non-OE parts with OE per Rhode Island statute"))
                        break  # One finding is enough
        except (ValueError, TypeError):
            pass

    # ── MN: must disclose non-OE parts ──
    if state == "MN":
        non_oe = []
        for line in parsed_lines:
            if (line.get("part_type") or "").strip().upper() in ("A/M", "AF", "LKQ"):
                ln = line.get("line_no")
                if ln and str(ln).isdigit(): non_oe.append(int(ln))
        if non_oe:
            findings.append(
                QCFinding(rule_id="STATEQC_011", category="state_compliance", severity="medium",
                    description=f"MN requires written disclosure for non-OE parts ({len(non_oe)} found)",
                    line_numbers=non_oe,
                    suggested_fix="Attach signed non-OE parts disclosure per Minnesota statute"))

    # ── WV: OE required for structural on vehicles < 3 years ──
    if state == "WV":
        try:
            veh_year = int(year_str)
            if veh_year >= 2023:
                structural_kw = ["frame", "rail", "apron", "pillar", "rocker", "cowl", "floor"]
                for line in parsed_lines:
                    panel = (line.get("panel_name") or "").strip().lower()
                    pt = (line.get("part_type") or "").strip().upper()
                    if pt in ("A/M", "AF") and any(kw in panel for kw in structural_kw):
                        ln = line.get("line_no")
                        findings.append(
                            QCFinding(rule_id="STATEQC_012", category="state_compliance", severity="critical",
                                description=f"WV requires OE structural parts on vehicles < 3 years",
                                line_numbers=[int(ln)] if ln and str(ln).isdigit() else [],
                                suggested_fix="Replace A/M structural parts with OE per West Virginia statute"))
                        break
        except (ValueError, TypeError):
            pass

    return findings


# ═══════════════════════════════════════════════════════════════════════
# CARRIER-SPECIFIC RULES (NatGen / IAnet Handbook v4)
# ═══════════════════════════════════════════════════════════════════════

def _check_carrier_rules(
    parsed_lines: list[dict[str, Any]], meta: dict[str, Any]
) -> list[QCFinding]:
    findings: list[QCFinding] = []

    # ── NATGEN_001: Scan labor > 0.5 hours ──
    for line in parsed_lines:
        desc = (line.get("description") or "").lower()
        if "scan" not in desc:
            continue
        lh = float(line.get("labor_hours") or 0)
        if lh > 0.5:
            ln = line.get("line_no")
            findings.append(
                QCFinding(rule_id="NATGEN_001", category="carrier", severity="high",
                    description=f"Scan billed at {lh}h — max allowance 0.5h per carrier guidelines",
                    line_numbers=[int(ln)] if ln and str(ln).isdigit() else [],
                    suggested_fix="Reduce scan to 0.5 labor hours maximum"))

    # ── NATGEN_004: OEM parts restriction (current MY + <15K mi) ──
    year_str = str(meta.get("year") or "").strip()
    odometer = str(meta.get("odometer") or "").strip()
    try:
        current_year = 2026
        veh_year = int(year_str) if year_str.isdigit() else 0
        mileage = int(odometer.replace(",", "")) if any(c.isdigit() for c in odometer) else 0
        oem_restricted = (veh_year < current_year) or (mileage >= 15000)

        if oem_restricted:
            for line in parsed_lines:
                pt = (line.get("part_type") or "").strip().upper()
                if pt in ("OE", "OEM", "OES") and float(line.get("part_price") or 0) > 0:
                    ln = line.get("line_no")
                    findings.append(
                        QCFinding(rule_id="NATGEN_004", category="carrier", severity="high",
                            description=f"OEM part may not qualify — requires current MY + <15K mi (vehicle: {veh_year}, {mileage:,} mi)",
                            line_numbers=[int(ln)] if ln and str(ln).isdigit() else [],
                            suggested_fix="Replace with LKQ recycled, reman, or A/M per NatGen parts hierarchy"))
                    break
    except (ValueError, TypeError):
        pass

    # ── NATGEN_006: Unjustified Replace on common panels ──
    high_risk = ["bumper", "fender", "door skin", "outer panel"]
    for line in parsed_lines:
        op = (line.get("operation") or "").strip()
        desc = (line.get("description") or "").lower()
        if op != "Repl":
            continue
        if any(kw in desc for kw in high_risk):
            ln = line.get("line_no")
            findings.append(
                QCFinding(rule_id="NATGEN_006", category="carrier", severity="medium",
                    description=f"Replace on {line.get('description','')} — default to repair per carrier guidelines",
                    line_numbers=[int(ln)] if ln and str(ln).isdigit() else [],
                    suggested_fix="Verify photos show severe damage. If repairable, change to repair operation"))

    # ── NATGEN_007: Unnecessary blend ──
    for line in parsed_lines:
        op = (line.get("operation") or "").strip()
        if op in ("Blend", "Blnd"):
            ln = line.get("line_no")
            findings.append(
                QCFinding(rule_id="NATGEN_007", category="carrier", severity="medium",
                    description=f"Blend on {line.get('description','')} — verify necessity (color match, panel separation)",
                    line_numbers=[int(ln)] if ln and str(ln).isdigit() else [],
                    suggested_fix="Verify blend is necessary for color match. Remove if panel separation exists or repair is minimal"))

    return findings


# ═══════════════════════════════════════════════════════════════════════
# TOMMY'S AUDIT BRAIN — high-signal production rules
# ═══════════════════════════════════════════════════════════════════════

def _check_tommy_rules(
    parsed_lines: list[dict[str, Any]], meta: dict[str, Any]
) -> list[QCFinding]:
    findings: list[QCFinding] = []

    # ── COVER_001: Cover car required with refinish ──
    has_refinish = any(
        str(r.get("operation", "")).strip() == "Ref" or 
        "refinish" in str(r.get("description", "")).lower()
        for r in parsed_lines
    )
    has_cover = any("cover car" in str(r.get("description", "")).lower() for r in parsed_lines)
    if has_refinish and not has_cover:
        findings.append(
            QCFinding(rule_id="COVER_001", category="carrier", severity="high",
                description="Refinish on estimate — cover car is missing (required when vehicle goes to paint booth)",
                suggested_fix="Add cover car to the estimate"))

    # ── FRAME_001: Frame set-up & measure ──
    has_frame = any(
        "frame" in str(r.get("description", "")).lower() or 
        "frame" in str(r.get("panel_name", "")).lower()
        for r in parsed_lines
    )
    has_setup = any(
        "set" in str(r.get("description", "")).lower() and 
        "measur" in str(r.get("description", "")).lower()
        for r in parsed_lines
    )
    if has_frame and not has_setup:
        findings.append(
            QCFinding(rule_id="FRAME_001", category="labor", severity="high",
                description="Frame damage detected — set-up and measure is missing (most commonly missed frame line)",
                suggested_fix="Add set-up and measure for frame damage"))

    # ── ALIGN_001: Alignment with tire/wheel damage ──
    has_tire_wheel = any(
        any(kw in str(r.get("description", "")).lower() for kw in ("tire", "wheel", "rim"))
        for r in parsed_lines
    )
    has_align = any("align" in str(r.get("description", "")).lower() for r in parsed_lines)
    if has_tire_wheel and not has_align:
        findings.append(
            QCFinding(rule_id="ALIGN_001", category="labor", severity="high",
                description="Tire/wheel damage detected — alignment may be warranted (impact shifts geometry)",
                suggested_fix="Review for wheel alignment. Add if tire/wheel damage confirmed"))

    # ── CHECK_006: Damage-to-value % required in notes for >$3K ──
    total = float(meta.get("total_estimate") or 0)
    if total > 3000:
        findings.append(
            QCFinding(rule_id="DAMVAL_001", category="carrier", severity="high",
                description=f"Estimate ${total:,.0f} — damage-to-value percentage must be in estimate notes. NO EXCEPTIONS per carrier guidelines",
                suggested_fix="Add damage-to-value percentage in estimate notes"))

    # ── ESCALATE_001: $10K+ estimate escalation ──
    if total > 10000:
        findings.append(
            QCFinding(rule_id="ESCALATE_001", category="carrier", severity="high" if total > 15000 else "medium",
                description=f"${total:,.0f} estimate — consider escalation. If unsure, contact supervisor before proceeding",
                suggested_fix="Review findings. If uncertain, escalate to manager"))

    return findings


# ═══════════════════════════════════════════════════════════════════════
# MOTOR GUIDE P-PAGE RULES
# ═══════════════════════════════════════════════════════════════════════

# MOTOR included operations: (parent_keyword, child_keyword) — if parent is on estimate, child R&I is INCLUDED
MOTOR_INCLUDED = [
    ("hood", "insulator"), ("hood", "hinge"), ("cowl", "cowl grille"), ("cowl", "wiper arm"),
    ("cowl", "wiper motor"), ("door", "belt molding"), ("door", "weatherstrip"), ("door", "mirror"),
    ("door", "handle"), ("door", "lock"), ("door", "latch"), ("door", "regulator"),
    ("door", "trim panel"), ("door", "door glass"), ("door", "run channel"),
    ("bumper", "bracket"), ("bumper", "reinforcement"), ("bumper", "absorber"), ("bumper", "impact bar"),
    ("fender", "liner"), ("fender", "splash shield"), ("roof", "headliner"), ("roof", "sunroof"),
    ("roof", "roof rack"), ("roof", "antenna"), ("liftgate", "trim panel"), ("liftgate", "glass"),
    ("liftgate", "wiper"), ("liftgate", "handle"), ("liftgate", "molding"), ("liftgate", "emblem"),
    ("liftgate", "nameplate"), ("quarter", "trim panel"), ("quarter", "glass"), ("quarter", "molding"),
    ("headlamp", "bracket"), ("headlamp", "mounting panel"), ("tail lamp", "bracket"),
    ("deck lid", "trim panel"), ("deck lid", "lock"), ("deck lid", "emblem"), ("deck lid", "nameplate"),
    ("deck lid", "spoiler"), ("radiator", "condenser"), ("radiator", "fan"),
    ("frame", "crossmember"), ("frame", "body mount"),
]

def _check_motor_rules(
    parsed_lines: list[dict[str, Any]], meta: dict[str, Any]
) -> list[QCFinding]:
    findings: list[QCFinding] = []

    # Build set of replace/repair parent panels
    replace_panels: set[str] = set()
    for line in parsed_lines:
        op = (line.get("operation") or "").strip()
        desc = (line.get("description") or "").lower()
        panel = (line.get("panel_name") or "").lower()
        if op == "Repl":
            for kw in ["hood", "door", "bumper", "fender", "roof", "quarter", "deck", "trunk",
                       "liftgate", "tail gate", "headlamp", "tail lamp", "radiator", "frame", "cowl"]:
                if kw in desc or kw in panel:
                    replace_panels.add(kw)

    for line in parsed_lines:
        if line.get("is_header"):
            continue
        op = (line.get("operation") or "").strip()
        desc = (line.get("description") or "").lower()
        if op not in ("R&I",):
            continue

        # Check MOTOR included pairs
        is_included = False
        for parent_kw, child_kw in MOTOR_INCLUDED:
            if child_kw in desc and parent_kw in replace_panels:
                is_included = True
                break

        if is_included:
            ln = line.get("line_no")
            findings.append(
                QCFinding(rule_id="MOTOR_001", category="carrier", severity="medium",
                    description=f"R&I of {line.get('description','')} may be included in parent operation per MOTOR P-pages",
                    line_numbers=[int(ln)] if ln and str(ln).isdigit() else [],
                    suggested_fix="Verify MOTOR P-pages — if R&I is included in parent op, remove separate charge"))

    return findings


# ═══════════════════════════════════════════════════════════════════════
# SUPPLEMENT DOCUMENTATION RULES
# ═══════════════════════════════════════════════════════════════════════

def _check_supplement_docs(
    parsed_lines: list[dict[str, Any]], meta: dict[str, Any]
) -> list[QCFinding]:
    findings: list[QCFinding] = []
    is_supp = meta.get("is_supplement", False)

    # These rules apply to supplements AND originals (any estimate line can be flagged)
    for line in parsed_lines:
        if line.get("is_header"):
            continue
        desc = (line.get("description") or "").lower()
        ln = line.get("line_no")
        ln_int = int(ln) if ln and str(ln).isdigit() else 0

        # ── Calibration requires invoice ──
        if any(kw in desc for kw in ["calibration", "aim", "adas", "radar", "target"]):
            price = float(line.get("part_price") or 0) + float(line.get("misc_amount") or 0)
            if price > 0:
                findings.append(
                    QCFinding(rule_id="SUPP_002", category="carrier", severity="high",
                        description=f"Calibration/ADAS on L{ln} (${price:.2f}) — supporting invoice required per carrier",
                        line_numbers=[ln_int],
                        suggested_fix="Attach calibration invoice or remove charge"))

        # ── Scan > 0.5h or has dollar amount — invoice required ──
        if "scan" in desc:
            lh = float(line.get("labor_hours") or 0)
            price = float(line.get("part_price") or 0) + float(line.get("misc_amount") or 0)
            if lh > 0.5 or price > 0:
                findings.append(
                    QCFinding(rule_id="SUPP_003", category="carrier", severity="high",
                        description=f"Scan charge on L{ln} — invoice/scan report required per carrier",
                        line_numbers=[ln_int],
                        suggested_fix="Attach scan report/invoice or reduce to 0.5h allowance"))

        # ── Wheel alignment — invoice required ──
        if any(kw in desc for kw in ["alignment", "align", "wheel align", "4 wheel align", "thrust align"]):
            findings.append(
                QCFinding(rule_id="SUPP_004", category="carrier", severity="high",
                    description=f"Wheel alignment on L{ln} — invoice required per carrier",
                    line_numbers=[ln_int],
                    suggested_fix="Attach alignment invoice"))

    return findings


# ═══════════════════════════════════════════════════════════════════════
# EXTENDED CARRIER RULES — remaining NatGen + Tommy's production rules
# ═══════════════════════════════════════════════════════════════════════

def _check_extended_rules(
    parsed_lines: list[dict[str, Any]], meta: dict[str, Any]
) -> list[QCFinding]:
    findings: list[QCFinding] = []

    # ── NATGEN_016: Safety systems — no A/M, LKQ/OEM only ──
    safety_kw = ["airbag", "seat belt", "seatbelt", "srs", "pretensioner", "clock spring",
                 "impact sensor", "occupant sensor", "restraint", "adas module", "radar sensor",
                 "camera module", "blind spot", "lane departure", "parking sensor"]
    for line in parsed_lines:
        desc = (line.get("description") or "").lower()
        pt = (line.get("part_type") or "").strip().upper()
        if pt in ("A/M", "AF") and any(kw in desc for kw in safety_kw):
            ln = line.get("line_no")
            findings.append(
                QCFinding(rule_id="NATGEN_016", category="carrier", severity="critical",
                    description=f"Safety system part must be LKQ/OEM — A/M prohibited: {line.get('description','')}",
                    line_numbers=[int(ln)] if ln and str(ln).isdigit() else [],
                    suggested_fix="Replace A/M safety part with LKQ recycled or OEM. Safety systems cannot use aftermarket"))

    # ── NATGEN_008: Unjustified R&I (cosmetic R&I flagging) ──
    cosmetic_ri = ["handle", "trim", "molding", "nameplate", "emblem", "badge", "wiper",
                   "weatherstrip", "belt molding", "run channel", "door glass"]
    for line in parsed_lines:
        op = (line.get("operation") or "").strip()
        desc = (line.get("description") or "").lower()
        if op == "R&I" and any(kw in desc for kw in cosmetic_ri):
            ln = line.get("line_no")
            findings.append(
                QCFinding(rule_id="NATGEN_008", category="carrier", severity="low",
                    description=f"Cosmetic R&I on {line.get('description','')} — verify repair access justification per carrier",
                    line_numbers=[int(ln)] if ln and str(ln).isdigit() else [],
                    suggested_fix="Verify R&I is required for repair access. Cosmetic R&I has higher revision risk"))

    # ── NATGEN_002: Calibration deferred to supplement ──
    is_supp = meta.get("is_supplement", False)
    for line in parsed_lines:
        desc = (line.get("description") or "").lower()
        if any(kw in desc for kw in ["calibration", "aim", "adas", "radar", "target", "sensor calibrat"]):
            price = float(line.get("part_price") or 0) + float(line.get("misc_amount") or 0)
            if price > 0 and not is_supp:
                ln = line.get("line_no")
                findings.append(
                    QCFinding(rule_id="NATGEN_002", category="carrier", severity="high",
                        description=f"Calibration charge on original estimate — should be deferred to supplement phase",
                        line_numbers=[int(ln)] if ln and str(ln).isdigit() else [],
                        suggested_fix="Defer calibration to supplement after scanning completed"))

    # ── CHECK_001: NADA required on estimates >$5K ──
    total = float(meta.get("total_estimate") or 0)
    if total > 5000:
        findings.append(
            QCFinding(rule_id="CHECK_001", category="carrier", severity="high",
                description=f"Estimate ${total:,.0f} — NADA Clean Retail valuation required per audit protocol",
                suggested_fix="Attach NADA Clean Retail valuation to estimate file"))

    return findings


# ═══════════════════════════════════════════════════════════════════════
# NEW AUDIT RULES — glass, bumper, suspension, emblem, markup
# ═══════════════════════════════════════════════════════════════════════

def _check_correlation_rules(
    parsed_lines: list[dict[str, Any]], meta: dict[str, Any]
) -> list[QCFinding]:
    findings: list[QCFinding] = []
    year_str = str(meta.get("year") or "").strip()

    # ── GLASS_001: Windshield replaced → ADAS calibration? ──
    try:
        veh_year = int(year_str) if year_str.isdigit() else 0
        has_windshield_repl = any(
            (line.get("operation") or "").strip() == "Repl" and 
            "windshield" in (line.get("description") or "").lower()
            for line in parsed_lines
        )
        has_calibration = any(
            any(kw in (line.get("description") or "").lower() for kw in ["calibration", "aim", "adas", "camera"])
            for line in parsed_lines
        )
        if veh_year >= 2018 and has_windshield_repl and not has_calibration:
            findings.append(
                QCFinding(rule_id="GLASS_001", category="carrier", severity="high",
                    description=f"Windshield replaced on {veh_year} vehicle — ADAS calibration likely required (camera/sensor behind windshield)",
                    suggested_fix="Add ADAS camera calibration if vehicle has forward-facing camera behind windshield"))
    except (ValueError, TypeError):
        pass

    # ── BUMPER_001: Bumper cover replaced → absorber/reinforcement addressed? ──
    has_bumper_repl = any(
        (line.get("operation") or "").strip() == "Repl" and 
        "bumper" in (line.get("description") or "").lower()
        for line in parsed_lines
    )
    has_absorber = any(
        any(kw in (line.get("description") or "").lower() for kw in ["absorber", "reinforcement", "impact bar"])
        for line in parsed_lines
    )
    if has_bumper_repl and not has_absorber:
        findings.append(
            QCFinding(rule_id="BUMPER_001", category="carrier", severity="medium",
                description="Bumper cover replaced — verify absorber/reinforcement/impact bar condition",
                suggested_fix="Inspect and document bumper absorber and reinforcement. Add replacement if damaged"))

    # ── SUSP_001: Suspension work → alignment required ──
    has_susp = any(
        any(kw in (line.get("description") or "").lower() for kw in 
            ["strut", "control arm", "tie rod", "ball joint", "steering knuckle", "shock",
             "spring", "steering rack", "steering gear", "sway bar", "trailing arm"])
        for line in parsed_lines
    )
    has_align = any("align" in (line.get("description") or "").lower() for line in parsed_lines)
    if has_susp and not has_align:
        findings.append(
            QCFinding(rule_id="SUSP_001", category="labor", severity="high",
                description="Suspension component work detected — wheel alignment should be included",
                suggested_fix="Add wheel alignment to estimate — geometry shifts with any suspension work"))

    # ── EMBLEM_001: Panel replaced → emblem/nameplate R&I is included ──
    for line in parsed_lines:
        op = (line.get("operation") or "").strip()
        desc = (line.get("description") or "").lower()
        if op == "R&I" and any(kw in desc for kw in ["emblem", "nameplate", "badge"]):
            # Check if parent panel is being replaced
            for parent in parsed_lines:
                p_op = (parent.get("operation") or "").strip()
                p_desc = (parent.get("description") or "").lower()
                if p_op == "Repl":
                    # Check if emblem is likely on this panel
                    panel = (parent.get("panel_name") or "").lower()
                    for kw in ["hood", "door", "fender", "quarter", "deck", "trunk", "liftgate", "tailgate"]:
                        if kw in panel and kw in p_desc:
                            ln = line.get("line_no")
                            findings.append(
                                QCFinding(rule_id="EMBLEM_001", category="carrier", severity="low",
                                    description=f"Emblem/nameplate R&I L{ln} may be included in panel replacement — verify",
                                    line_numbers=[int(ln)] if ln and str(ln).isdigit() else [],
                                    suggested_fix="Per MOTOR P-pages, emblem R&I is typically included when parent panel is replaced. Remove if duplicate."))
                            break

    # ── MARKUP_001: Part price >25% above list ──
    for line in parsed_lines:
        price = float(line.get("part_price") or 0)
        if price > 500:  # Only check significant parts
            desc = (line.get("description") or "").lower()
            # Rough list price estimates for common panels
            list_estimates = {"hood": 400, "door": 500, "fender": 250, "bumper": 350,
                             "quarter": 600, "deck": 400, "headlamp": 300, "tail lamp": 200}
            for panel, est in list_estimates.items():
                if panel in desc and price > est * 1.25:
                    ln = line.get("line_no")
                    findings.append(
                        QCFinding(rule_id="MARKUP_001", category="financial", severity="medium",
                            description=f"Part price ${price:.0f} appears above typical range for {panel} — verify against invoice",
                            line_numbers=[int(ln)] if ln and str(ln).isdigit() else [],
                            suggested_fix="Verify part price against dealer invoice or list price. Document if verified"))

    return findings


# ═══════════════════════════════════════════════════════════════════════
# FINAL BATCH — all remaining v1 production rules
# ═══════════════════════════════════════════════════════════════════════

def _check_final_rules(
    parsed_lines: list[dict[str, Any]], meta: dict[str, Any]
) -> list[QCFinding]:
    findings: list[QCFinding] = []
    is_supp = meta.get("is_supplement", False)
    total = float(meta.get("total_estimate") or 0)

    # ── AUDIT_007: Negative labor (not legitimate overlap/deduction) ──
    legit_neg = ["overlap", "deduction", "deduct", "discount", "reduction",
                 "credit", "less", "adjustment", "adj", "negotiated"]
    for line in parsed_lines:
        lh = float(line.get("labor_hours") or 0)
        desc = (line.get("description") or "").lower()
        price = float(line.get("part_price") or 0)
        if lh < 0 or (lh == 0 and price < 0 and abs(price) >= 25):
            if any(kw in desc for kw in legit_neg):
                continue
            ln = line.get("line_no")
            findings.append(
                QCFinding(rule_id="AUDIT_007", category="labor", severity="high",
                    description=f"Unexplained negative labor on L{ln} (${price:.2f} / {lh}h) — not a standard deduction",
                    line_numbers=[int(ln)] if ln and str(ln).isdigit() else [],
                    suggested_fix="If legitimate overlap/discount: document. Otherwise: reject and correct"))

    # ── AUDIT_008: Labor $ without hours ──
    flat_rate = ["prime and block", "clear bra", "mud guard", "transport",
                 "corrosion protection", "safety inspection", "denib", "tint",
                 "polish", "buff", "detail", "wash", "clean", "mask", "cover car",
                 "flex additive", "haz", "waste", "supply", "shop supply", "material", "sundries",
                 "rotor", "brake pad", "brake pads", "drum", "caliper", "wheel cylinder",
                 "sensor", "switch", "bulb", "lamp assy", "wiper blade", "filter",
                 "belt", "hose", "clamp", "clip", "retainer", "fastener", "cap", "plug"]
    for line in parsed_lines:
        lh = float(line.get("labor_hours") or 0)
        price = float(line.get("part_price") or 0)
        desc = (line.get("description") or "").lower()
        if price > 0 and lh == 0 and "scan" not in desc and not any(kw in desc for kw in flat_rate):
            if price >= 100:
                ln = line.get("line_no")
                findings.append(
                    QCFinding(rule_id="AUDIT_008", category="labor", severity="high",
                        description=f"Labor ${price:.2f} billed without hours on L{ln} — {line.get('description','')[:50]}",
                        line_numbers=[int(ln)] if ln and str(ln).isdigit() else [],
                        suggested_fix="If hourly labor: add hours. If flat-rate: ignore"))

    # ── AUDIT_009: Zero-price part ──
    for line in parsed_lines:
        pn = line.get("part_number") or ""
        price = float(line.get("part_price") or 0)
        misc = float(line.get("misc_amount") or 0) if "misc_amount" in str(line) else 0
        if pn and price == 0 and misc == 0:
            ln = line.get("line_no")
            findings.append(
                QCFinding(rule_id="AUDIT_009", category="parts", severity="low",
                    description=f"Part #{pn} on L{ln} has $0.00 price — verify if manually overridden",
                    line_numbers=[int(ln)] if ln and str(ln).isdigit() else [],
                    suggested_fix="Review justification for zero-price part entry"))

    # ── AUDIT_010: Mechanical labor on cosmetic file ──
    has_mech = any(
        float(line.get("labor_hours") or 0) > 0 and 
        any(kw in (line.get("description") or "").lower() for kw in 
            ["mechanical", "diagnostic", "diag", "engine", "transmission", "suspension",
             "steering", "brake", "exhaust", "driveline", "differential", "transfer case"])
        for line in parsed_lines
    )
    has_structural = any(
        any(kw in (line.get("description") or "").lower() for kw in ["frame", "rail", "apron", "pillar"])
        for line in parsed_lines
    )
    if has_mech and not has_structural:
        findings.append(
            QCFinding(rule_id="AUDIT_010", category="labor", severity="medium",
                description="Mechanical/diagnostic labor detected on cosmetic estimate (no structural damage)",
                suggested_fix="Confirm mechanical operations are tied to direct collision impact"))

    # ── NATGEN_022: Total loss — write 100% of damages ──
    if total > 10000:
        findings.append(
            QCFinding(rule_id="NATGEN_022", category="carrier", severity="medium",
                description=f"${total:,.0f} estimate — write 100% of damages per carrier guidelines. Do not stop at total loss threshold",
                suggested_fix="Ensure all damages are documented completely. Do not omit damages because threshold is near"))

    # ── NATGEN_010: Sublet documentation required ──
    for line in parsed_lines:
        desc = (line.get("description") or "").lower()
        price = float(line.get("part_price") or 0)
        if (any(kw in desc for kw in ["sublet", "subl", "tow", "storage"]) or 
            line.get("operation") == "SUBLET") and price > 0:
            ln = line.get("line_no")
            findings.append(
                QCFinding(rule_id="NATGEN_010", category="carrier", severity="high",
                    description=f"Sublet charge ${price:.2f} on L{ln} requires supporting invoice per carrier",
                    line_numbers=[int(ln)] if ln and str(ln).isdigit() else [],
                    suggested_fix="Attach supporting invoice. Dealer mechanical invoices must be itemized by operation"))

    # ── SUPP_005: Sublet on supplement → invoice required ──
    if is_supp:
        for line in parsed_lines:
            desc = (line.get("description") or "").lower()
            price = float(line.get("part_price") or 0)
            is_sublet = any(kw in desc for kw in ["sublet", "subl", "tow", "storage", "glass",
                                                   "alignment", "align", "calibration", "scan",
                                                   "pdr", "dent", "hail"])
            if is_sublet and price > 0:
                ln = line.get("line_no")
                findings.append(
                    QCFinding(rule_id="SUPP_005", category="carrier", severity="high",
                        description=f"Sublet on supplement L{ln} (${price:.2f}) — invoice required per carrier",
                        line_numbers=[int(ln)] if ln and str(ln).isdigit() else [],
                        suggested_fix="Attach supporting invoice. Without documentation, carrier will remove the charge"))

    # ── HAIL_002: Hail windshield causation ──
    has_hail = any("hail" in (line.get("description") or "").lower() for line in parsed_lines)
    if has_hail:
        for line in parsed_lines:
            desc = (line.get("description") or "").lower()
            op = (line.get("operation") or "").strip()
            if ("windshield" in desc or "glass" in desc) and op == "Repl":
                ln = line.get("line_no")
                findings.append(
                    QCFinding(rule_id="HAIL_002", category="carrier", severity="high",
                        description=f"Windshield replacement on hail claim L{ln} — verify hail directly caused break (rock chips don't qualify)",
                        line_numbers=[int(ln)] if ln and str(ln).isdigit() else [],
                        suggested_fix="Verify windshield break in hail photos. If rock chip, remove or document as unrelated"))

    # ── CHECK_004: Production date ──
    if not meta.get("production_date"):
        findings.append(
            QCFinding(rule_id="CHECK_004", category="completeness", severity="low",
                description="Vehicle production date not on estimate — needed for parts compatibility",
                suggested_fix="Include vehicle build/production date for correct parts selection"))

    return findings
