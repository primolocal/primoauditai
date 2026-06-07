"""
NatGen carrier-specific rules (NATGEN_001-022).
Derived from NatGen Auditor Handbook v4 + IANet/National General guidelines.
"""

from src.engine.base import BaseRule, RuleResult
from src.engine.context import AuditContext

# --- Calibration helpers (shared) ---

def _is_calibration_line(line: dict) -> bool:
    """Detect calibration/aim/sensor lines with false-positive filtering."""
    desc = str(line.get("description", "")).lower()
    srv = str(line.get("service_subtype", ""))
    # Exclude headlights from calibration triggers
    if "headlight" in desc or "headlamp" in desc:
        return False
    # Core calibration keywords
    if srv in ["calibration", "aim", "sensor_aim"]:
        return True
    if any(w in desc for w in ["calibration", "aim", "target", "adas"]):
        return True
    # "sensor" only when paired with calibration-related terms (avoids "park sensor" false match)
    return "sensor" in desc and any(kw in desc for kw in ["calibrat", "aim", "adas", "radar"])


def _calibration_charge(line: dict) -> float:
    """Total dollar charge on a calibration line."""
    fs = line.get("financial_signature", {})
    return fs.get("part_price", 0) + fs.get("misc_amount", 0) + fs.get("labor_amount_total", 0)


def _is_original_estimate(line: dict) -> bool:
    """True if line is on original estimate (E01 or no supplement)."""
    supp = str(line.get("supplement", "")).upper()
    return (not supp) or supp == "E01"


# --- Rules ---

class ScanLaborThresholdRule(BaseRule):
    """NATGEN_001: Scan labor >0.5 hrs, or scan with $ amount missing invoice."""
    rule_id = "NATGEN_001"
    category = "carrier_compliance"
    description = "Scan labor exceeds 0.5hr allowance or scan charge lacks documentation"
    severity = "medium"

    def applies(self, ctx: AuditContext) -> bool:
        return True

    def evaluate(self, ctx: AuditContext) -> list[RuleResult]:
        results = []
        for line in ctx.get_all_lines():
            desc = str(line.get("description", "")).lower()
            if "scan" not in desc and line.get("service_subtype") != "scan":
                continue
            fs = line.get("financial_signature", {})
            l_hrs = fs.get("labor_hours_total", 0)
            # 1. Hours > 0.5
            if l_hrs > 0.5:
                results.append(RuleResult(
                    rule_id=self.rule_id,
                    category=self.category,
                    severity="high",
                    description=self.description,
                    line_numbers=[line.get("line_no")],
                    summary=f"Scan billed at {l_hrs} hours (max allowance: 0.5).",
                    detail="Carrier guidelines strictly allow 0.5 for pre and post scans.",
                    action="Reduce operation to 0.5 labor hours.",
                ))
            # 2. Dollar amount requires documentation
            tot_charge = fs.get("part_price", 0) + fs.get("misc_amount", 0)
            if tot_charge > 0:
                results.append(RuleResult(
                    rule_id=self.rule_id,
                    category="documentation_readiness",
                    severity="high",
                    description="Scan carries dollar amount but is missing supporting documentation",
                    line_numbers=[line.get("line_no")],
                    summary="Scan carries a dollar amount but is missing supporting documentation.",
                    detail="Any dollar amount listed for scans must be directly supported with documentation (invoice or report).",
                    action="Request scan report or sublet invoice.",
                ))
        return results


class CalibrationChargeTimingRule(BaseRule):
    """NATGEN_002: Calibration should not carry charges on original estimate (E01)."""
    rule_id = "NATGEN_002"
    category = "carrier_compliance"
    description = "Calibration charges on original estimate — must be deferred to supplement"
    severity = "high"

    def applies(self, ctx: AuditContext) -> bool:
        return True

    def evaluate(self, ctx: AuditContext) -> list[RuleResult]:
        results = []
        for line in ctx.get_all_lines():
            if not _is_calibration_line(line):
                continue
            charge = _calibration_charge(line)
            if charge == 0:
                continue
            if _is_original_estimate(line):
                results.append(RuleResult(
                    rule_id=self.rule_id,
                    category=self.category,
                    severity=self.severity,
                    description=self.description,
                    line_numbers=[line.get("line_no")],
                    summary="Calibration/Aim procedures should not carry charges on original estimates (E01).",
                    detail="Carrier requires calibration charges to be deferred to supplement phase after scanning.",
                    action="Defer to supplement.",
                ))
            else:
                # Supplement calibration — check for docs
                has_docs = any(
                    rl.get("is_sublet", False) or rl.get("row_type") == "sublet"
                    for rl in ctx.get_all_lines()
                    if any(k in str(rl.get("description", "")).lower() for k in ["scan", "calibration", "adas", "report", "invoice"])
                )
                if not has_docs:
                    results.append(RuleResult(
                        rule_id=self.rule_id,
                        category="documentation_readiness",
                        severity="medium",
                        description="Supplement calibration lacks invoice/scan support",
                        line_numbers=[line.get("line_no")],
                        summary="Calibration/Aim billed on supplement without invoice/scan support.",
                        detail="Calibration charges require document/invoice support when requested on supplement.",
                        action="Request sublet invoice or scan report.",
                    ))
        return results


class CalibrationTriggerSupportRule(BaseRule):
    """NATGEN_003: Calibration must have trigger parts (bumper, radar, sensor, etc.)."""
    rule_id = "NATGEN_003"
    category = "documentation_readiness"
    description = "Calibration billed without related trigger parts on estimate"
    severity = "medium"

    STRONG_KWS = ["bumper", "impact bar", "reinforcement", "grille", "radar", "sensor", "windshield", "camera", "mirror", "module"]
    WEAK_KWS = ["trim", "reflector", "molding", "o/h", "overhaul"]

    def applies(self, ctx: AuditContext) -> bool:
        return True

    def evaluate(self, ctx: AuditContext) -> list[RuleResult]:
        results = []
        all_lines = ctx.get_all_lines()
        for line in all_lines:
            if not _is_calibration_line(line):
                continue
            charge = _calibration_charge(line)
            if charge == 0:
                continue

            strong = False
            weak = False
            for check in all_lines:
                if check.get("line_no") == line.get("line_no"):
                    continue
                c_desc = f"{check.get('description', '')} {check.get('operation_label', '')}".lower()
                if any(kw in c_desc for kw in self.STRONG_KWS):
                    strong = True
                    break
                elif any(kw in c_desc for kw in self.WEAK_KWS):
                    weak = True

            if strong:
                continue

            if weak:
                results.append(RuleResult(
                    rule_id=self.rule_id,
                    category=self.category,
                    severity="low",
                    description="Calibration with limited trigger support",
                    line_numbers=[line.get("line_no")],
                    summary="Calibration/Aim present with limited related trigger support.",
                    detail="Weak trigger parts identified for calibration.",
                    action="Verify structural necessity.",
                ))
            elif _is_original_estimate(line):
                results.append(RuleResult(
                    rule_id=self.rule_id,
                    category="carrier_compliance",
                    severity="high",
                    description="Calibration without trigger parts on original estimate",
                    line_numbers=[line.get("line_no")],
                    summary="Calibration/Aim billed without related trigger part on original estimate.",
                    detail="No radar/sensor/bumper trigger parts present on estimate sequence.",
                    action="Remove unsupported calibration charge.",
                ))
            else:
                results.append(RuleResult(
                    rule_id=self.rule_id,
                    category=self.category,
                    severity="medium",
                    description="Calibration on supplement without clear trigger part",
                    line_numbers=[line.get("line_no")],
                    summary="Calibration billed on supplement without clear trigger part.",
                    detail="No clear trigger operation found for supplement calibration charge.",
                    action="Request explanation from shop.",
                ))
        return results


class OEMPartRestrictionRule(BaseRule):
    """NATGEN_004: OEM only when current model year AND under 15,000 miles."""
    rule_id = "NATGEN_004"
    category = "parts_accuracy"
    description = "OEM part may not qualify — NatGen requires current year + <15K miles"
    severity = "high"

    def applies(self, ctx: AuditContext) -> bool:
        return True

    def evaluate(self, ctx: AuditContext) -> list[RuleResult]:
        results = []
        vehicle = ctx.metadata.get("vehicle", {})
        model_year = vehicle.get("year") or ctx.metadata.get("model_year")
        mileage = vehicle.get("mileage") or ctx.metadata.get("mileage")
        import datetime
        current_year = datetime.datetime.now().year

        for line in ctx.get_all_lines():
            if line.get("is_header"):
                continue
            pt = str(line.get("part_type", "")).upper()
            if pt not in ("OEM", "OES"):
                continue
            p_price = line.get("financial_signature", {}).get("part_price", 0)
            if p_price == 0:
                continue

            issues = []
            if model_year:
                try:
                    if int(model_year) < current_year:
                        issues.append(f"Not current model year (vehicle is {model_year})")
                except (ValueError, TypeError):
                    pass
            if mileage:
                try:
                    if int(mileage) >= 15000:
                        issues.append(f"Mileage {int(mileage):,} exceeds 15,000 limit")
                except (ValueError, TypeError):
                    pass

            if issues:
                results.append(RuleResult(
                    rule_id=self.rule_id,
                    category=self.category,
                    severity=self.severity,
                    description=self.description,
                    line_numbers=[line.get("line_no")],
                    summary=f"OEM part may not qualify — {', '.join(issues)}",
                    detail="NatGen requires both current model year AND under 15,000 miles for OEM parts.",
                    action="Replace with LKQ recycled, remanufactured, or aftermarket part per NatGen parts hierarchy.",
                ))
        return results


class UnjustifiedReplaceRule(BaseRule):
    """NATGEN_006: Default to repair. Replace must be justified."""
    rule_id = "NATGEN_006"
    category = "line_item_support"
    description = "Replace operation — verify repair is not viable"
    severity = "medium"

    HIGH_RISK_PANELS = ["bumper", "fender", "door skin", "outer panel", "quarter panel"]

    def applies(self, ctx: AuditContext) -> bool:
        return True

    def evaluate(self, ctx: AuditContext) -> list[RuleResult]:
        results = []
        for line in ctx.get_all_lines():
            if line.get("is_header"):
                continue
            desc = str(line.get("description", "")).lower()
            op = str(line.get("operation_label", "")).lower()
            if op != "replace":
                continue
            if "corrosion protection" in desc:
                continue
            is_high = any(kw in desc for kw in self.HIGH_RISK_PANELS)
            pt = str(line.get("part_type", "")).upper()
            if is_high or pt not in ("OEM", "OES", "PAA", "PAR"):
                results.append(RuleResult(
                    rule_id=self.rule_id,
                    category=self.category,
                    severity=self.severity,
                    description=self.description,
                    line_numbers=[line.get("line_no")],
                    summary=f"Replace operation on {line.get('description', '')} — verify repair is not viable.",
                    detail="NatGen defaults to repair. Replace must be justified by severe damage, safety concern, or documented repair impracticality.",
                    action="Verify photos show severe damage. If repairable, change to repair operation.",
                ))
        return results


class UnnecessaryBlendRule(BaseRule):
    """NATGEN_007: Avoid blending when color match is likely or repair area is minimal."""
    rule_id = "NATGEN_007"
    category = "line_item_support"
    description = "Blend panel may be unnecessary — verify necessity"
    severity = "medium"

    def applies(self, ctx: AuditContext) -> bool:
        return True

    def evaluate(self, ctx: AuditContext) -> list[RuleResult]:
        results = []
        for line in ctx.get_all_lines():
            if line.get("is_header"):
                continue
            desc = str(line.get("description", "")).lower()
            op = str(line.get("operation_label", "")).lower()
            if op != "blend" and "blend" not in desc:
                continue
            # Adjacent panel checks
            adjacent_blend = any(
                other.get("line_no") != line.get("line_no")
                and str(other.get("operation_label", "")).lower() == "blend"
                for other in ctx.get_all_lines()
            )
            if not adjacent_blend:
                results.append(RuleResult(
                    rule_id=self.rule_id,
                    category=self.category,
                    severity=self.severity,
                    description=self.description,
                    line_numbers=[line.get("line_no")],
                    summary=f"Blend on {line.get('description', '')} — verify necessity.",
                    detail="Blends must be necessary — not routine. Avoid when color match is likely or repair area is minimal.",
                    action="Confirm blend is required. If not, remove.",
                ))
        return results


class UnjustifiedRIOperationsRule(BaseRule):
    """NATGEN_008: R&I operations must be justified by adjacent panel work."""
    rule_id = "NATGEN_008"
    category = "line_item_support"
    description = "R&I operation may lack justification — verify adjacent panel work"
    severity = "medium"

    def applies(self, ctx: AuditContext) -> bool:
        return True

    def evaluate(self, ctx: AuditContext) -> list[RuleResult]:
        results = []
        for line in ctx.get_all_lines():
            if line.get("is_header"):
                continue
            desc = str(line.get("description", "")).lower()
            op = str(line.get("operation_label", "")).lower()
            if "r&i" not in desc and op not in ("r&i", "remove & install"):
                continue
            # Check for adjacent repair/refinish work
            panel = str(line.get("panel_name", "")).lower()
            has_adjacent = any(
                other.get("line_no") != line.get("line_no")
                and str(other.get("panel_name", "")).lower() == panel
                and str(other.get("operation_label", "")).lower() in ("repair", "replace", "refinish")
                for other in ctx.get_all_lines()
            )
            if not has_adjacent:
                results.append(RuleResult(
                    rule_id=self.rule_id,
                    category=self.category,
                    severity=self.severity,
                    description=self.description,
                    line_numbers=[line.get("line_no")],
                    summary=f"R&I on {line.get('description', '')} — verify adjacent panel work justifies removal.",
                    detail="R&I operations must be justified by adjacent panel work (repair, replace, or refinish).",
                    action="Confirm adjacent panel requires R&I. If not, remove.",
                ))
        return results


class ExcessivePaintScopeRule(BaseRule):
    """NATGEN_012: Excessive paint scope — 3+ panels flagged for review."""
    rule_id = "NATGEN_012"
    category = "carrier_compliance"
    description = "Paint scope exceeds 3 panels — verify necessity"
    severity = "medium"

    def applies(self, ctx: AuditContext) -> bool:
        return True

    def evaluate(self, ctx: AuditContext) -> list[RuleResult]:
        refinish_panels = set()
        for line in ctx.get_all_lines():
            op = str(line.get("operation_label", "")).lower()
            if op == "refinish":
                refinish_panels.add(str(line.get("panel_name", "")).lower())
        if len(refinish_panels) >= 3:
            return [RuleResult(
                rule_id=self.rule_id,
                category=self.category,
                severity=self.severity,
                description=self.description,
                line_numbers=[],
                summary=f"{len(refinish_panels)} panels scheduled for refinish — verify paint scope necessity.",
                detail="NatGen: excessive paint scope (3+ panels) requires review. Each panel must be independently justified.",
                action="Review each refinish panel. Remove unnecessary panels.",
            )]
        return []


class ShopInfoRule(BaseRule):
    """NATGEN_011: Shop information must be complete on all estimates."""
    rule_id = "NATGEN_011"
    category = "documentation_readiness"
    description = "Shop name, address, or phone missing from estimate"
    severity = "high"

    def applies(self, ctx: AuditContext) -> bool:
        return True

    def evaluate(self, ctx: AuditContext) -> list[RuleResult]:
        shop = ctx.metadata.get("shop", {})
        missing = []
        if not shop.get("name"):
            missing.append("shop name")
        if not shop.get("address"):
            missing.append("address")
        if not shop.get("phone"):
            missing.append("phone")
        if missing:
            return [RuleResult(
                rule_id=self.rule_id,
                category=self.category,
                severity=self.severity,
                description=self.description,
                line_numbers=[],
                summary=f"Shop information incomplete — missing: {', '.join(missing)}.",
                detail="NatGen requires shop name, address, and phone number on all estimates and supplements.",
                action="Complete repair facility information.",
            )]
        return []


class DocumentationRule(BaseRule):
    """NATGEN_010: Missing sublet documentation — charges >$50 need invoice."""
    rule_id = "NATGEN_010"
    category = "documentation_readiness"
    description = "Sublet charge exceeding $50 without supporting invoice"
    severity = "high"

    def applies(self, ctx: AuditContext) -> bool:
        return True

    def evaluate(self, ctx: AuditContext) -> list[RuleResult]:
        results = []
        for line in ctx.get_all_lines():
            if not line.get("is_sublet", False) and line.get("row_type") != "sublet":
                continue
            amt = line.get("financial_signature", {}).get("misc_amount", 0)
            if amt > 50:
                results.append(RuleResult(
                    rule_id=self.rule_id,
                    category=self.category,
                    severity=self.severity,
                    description=self.description,
                    line_numbers=[line.get("line_no")],
                    summary=f"Sublet charge ${amt:.2f} on line {line.get('line_no')} — invoice required.",
                    detail="NatGen requires supporting invoice for all sublet charges exceeding $50.",
                    action="Provide sublet invoice or remove charge.",
                ))
        return results


class NoBodyShopSuppliesRule(BaseRule):
    """NATGEN_013: Body shop supplies not allowed as line items."""
    rule_id = "NATGEN_013"
    category = "carrier_compliance"
    description = "Body shop supplies charged as separate line items — not permitted"
    severity = "medium"

    def applies(self, ctx: AuditContext) -> bool:
        return True

    def evaluate(self, ctx: AuditContext) -> list[RuleResult]:
        results = []
        for line in ctx.get_all_lines():
            desc = str(line.get("description", "")).lower()
            if "shop supply" in desc or "body supply" in desc or "material" in desc and "sundries" in desc:
                results.append(RuleResult(
                    rule_id=self.rule_id,
                    category=self.category,
                    severity=self.severity,
                    description=self.description,
                    line_numbers=[line.get("line_no")],
                    summary=f"Body shop supplies line {line.get('line_no')} — not permitted as separate item.",
                    detail="NatGen: body shop supplies must be included in paint material calculation, not billed as separate line items.",
                    action="Remove body shop supplies line. Include in paint material instead.",
                ))
        return results


class NoLKQSuspensionRule(BaseRule):
    """NATGEN_015: LKQ suspension parts not permitted — safety critical."""
    rule_id = "NATGEN_015"
    category = "carrier_compliance"
    description = "LKQ/aftermarket suspension part detected — safety system requires OEM"
    severity = "high"

    def applies(self, ctx: AuditContext) -> bool:
        return True

    def evaluate(self, ctx: AuditContext) -> list[RuleResult]:
        results = []
        suspension_keywords = ["strut", "shock", "control arm", "ball joint", "tie rod", "spring", "suspension"]
        for line in ctx.get_all_lines():
            desc = str(line.get("description", "")).lower()
            pt = str(line.get("part_type", "")).upper()
            if pt in ("LKQ", "A/M", "AFM") and any(kw in desc for kw in suspension_keywords):
                results.append(RuleResult(
                    rule_id=self.rule_id,
                    category=self.category,
                    severity=self.severity,
                    description=self.description,
                    line_numbers=[line.get("line_no")],
                    summary=f"LKQ suspension part on {line.get('description', '')} — not permitted.",
                    detail="NatGen: LKQ/aftermarket suspension parts are not permitted. Safety-critical components require OEM.",
                    action="Replace with OEM part.",
                ))
        return results


class HazWasteCapRule(BaseRule):
    """NATGEN_020: Hazardous waste cap — verify carrier allowance."""
    rule_id = "NATGEN_020"
    category = "carrier_compliance"
    description = "Hazardous waste charge may exceed carrier cap"
    severity = "low"

    def applies(self, ctx: AuditContext) -> bool:
        return True

    def evaluate(self, ctx: AuditContext) -> list[RuleResult]:
        results = []
        for line in ctx.get_all_lines():
            desc = str(line.get("description", "")).lower()
            if "haz" in desc and "waste" in desc:
                amt = line.get("financial_signature", {}).get("misc_amount", 0)
                if amt > 25:
                    results.append(RuleResult(
                        rule_id=self.rule_id,
                        category=self.category,
                        severity=self.severity,
                        description=self.description,
                        line_numbers=[line.get("line_no")],
                        summary=f"Haz waste ${amt:.2f} may exceed carrier cap.",
                        detail="Verify carrier allowance logic allows direct line-item bill for haz waste.",
                        action="Confirm carrier cap or remove charge.",
                    ))
        return results


class NoFlexAdditiveRule(BaseRule):
    """NATGEN_014: Flex additive not allowed when not applicable."""
    rule_id = "NATGEN_014"
    category = "carrier_compliance"
    description = "Flex additive charge present — verify panel material requires it"
    severity = "low"

    def applies(self, ctx: AuditContext) -> bool:
        return True

    def evaluate(self, ctx: AuditContext) -> list[RuleResult]:
        results = []
        for line in ctx.get_all_lines():
            desc = str(line.get("description", "")).lower()
            if "flex" in desc and "add" in desc:
                # Check if panel is plastic/flexible material
                panel = str(line.get("panel_name", "")).lower()
                plastic_panels = ["bumper", "fascia", "trim", "molding", "spoiler", "valance"]
                if not any(p in panel for p in plastic_panels):
                    results.append(RuleResult(
                        rule_id=self.rule_id,
                        category=self.category,
                        severity=self.severity,
                        description=self.description,
                        line_numbers=[line.get("line_no")],
                        summary=f"Flex additive on {line.get('description', '')} — panel may not require it.",
                        detail="Flex additive only applicable on plastic/flexible panels (bumper, fascia, trim, etc.).",
                        action="Verify panel material. Remove if not plastic.",
                    ))
        return results


class TotalLossWriteFullRule(BaseRule):
    """NATGEN_022: Total loss — write complete damages, do not hold back."""
    rule_id = "NATGEN_022"
    category = "carrier_compliance"
    description = "Total loss estimate may be incomplete — write ALL damages"
    severity = "high"

    def applies(self, ctx: AuditContext) -> bool:
        return ctx.total_estimate() > 10000

    def evaluate(self, ctx: AuditContext) -> list[RuleResult]:
        total = ctx.total_estimate()
        return [RuleResult(
            rule_id=self.rule_id,
            category=self.category,
            severity=self.severity,
            description=self.description,
            line_numbers=[],
            summary=f"${total:,.0f} estimate — verify ALL damages are written on total loss.",
            detail="NatGen: on total loss files, write complete damages. Do not hold back operations to keep under threshold.",
            action="Review for missed operations. Write everything.",
        )]


class SafetySystemLKQRule(BaseRule):
    """NATGEN_016: LKQ parts on safety systems not permitted."""
    rule_id = "NATGEN_016"
    category = "carrier_compliance"
    description = "LKQ/aftermarket part on safety system — OEM required"
    severity = "high"

    SAFETY_KEYWORDS = [
        "airbag", "seat belt", "pretensioner", "sensor", "control module",
        "abs", "brake", "air bag", "srs", "restraint", "impact", "collision",
    ]

    def applies(self, ctx: AuditContext) -> bool:
        return True

    def evaluate(self, ctx: AuditContext) -> list[RuleResult]:
        results = []
        for line in ctx.get_all_lines():
            desc = str(line.get("description", "")).lower()
            pt = str(line.get("part_type", "")).upper()
            if pt in ("LKQ", "A/M", "AFM") and any(kw in desc for kw in self.SAFETY_KEYWORDS):
                results.append(RuleResult(
                    rule_id=self.rule_id,
                    category=self.category,
                    severity=self.severity,
                    description=self.description,
                    line_numbers=[line.get("line_no")],
                    summary=f"LKQ part on safety system {line.get('description', '')} — not permitted.",
                    detail="NatGen: LKQ/aftermarket parts on safety systems are not permitted. Safety-critical components require OEM.",
                    action="Replace with OEM part.",
                ))
        return results
