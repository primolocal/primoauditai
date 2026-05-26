"""
NatGen Carrier-Specific Rules — derived from NatGen Auditor Handbook v4 (v1.2)
AND IANet/National General Client Guidelines.
Covers Parts, Repair/Replace, Blends, R&I, Documentation, Paint Scope, OEM restrictions,
Safety parts, Betterment, Hazardous Waste, Flex Additive, Total Loss, Shop Supplies.
"""
from typing import List
from audit_context import AuditContext
from rules.base import BaseRule, RuleResult


# ============================================================================
# NatGen Core Rules (formerly natgen_rules.py)
# ============================================================================

class ScanLaborThresholdRule(BaseRule):
    rule_id = "NATGEN_001"
    title = "NatGen Scan Parameters"
    category = "carrier_compliance"
    severity = "medium"
    
    def applies(self, ctx: AuditContext) -> bool:
        return True
        
    def evaluate(self, ctx: AuditContext) -> List[RuleResult]:
        results = []
        for line in ctx.get_all_lines():
            desc = line.get("description", "").lower()
            if "scan" in desc or line.get("service_subtype") == "scan":
                fs = line.get("financial_signature", {})
                l_hrs = fs.get("labor_hours_total", 0)
                
                # 1. 0.5 allowance enforcement
                if l_hrs > 0.5:
                    results.append(RuleResult(
                        rule_id=self.rule_id,
                        title="Scan Labor Exceeds Allowance",
                        category=self.category,
                        severity="high",
                        affected_lines=[line.get("line_no")],
                        summary=f"Scan billed at {l_hrs} hours (Max allowance: 0.5).",
                        why_flagged="Carrier guidelines strictly allow 0.5 for pre and post scans.",
                        recommended_actions="Reduce operation to 0.5 labor hours."
                    ))
                
                # 2. Dollar amount requires documentation enforcement
                tot_charge = fs.get("part_price", 0) + fs.get("misc_amount", 0)
                if tot_charge > 0:
                    import uuid
                    scan_doc = next((d for d in ctx.documents if d.get("doc_type") in ["scan_pdf", "invoice"]), None)
                    if scan_doc:
                        ev_ref = {
                             "id": f"ev_{uuid.uuid4().hex[:6]}",
                             "type": "scan_pdf",
                             "source_id": scan_doc.get("id"),
                             "label": "Scan Support",
                             "support_status": "full",
                             "reason": "Provided dollar amount for scan is supported by appropriate documentation.",
                             "url": scan_doc.get("source_url"),
                             "thumbnail_url": scan_doc.get("thumbnail_url"),
                             "is_mock": scan_doc.get("is_mock", False)
                        }
                    else:
                        results.append(RuleResult(
                            rule_id=self.rule_id,
                            title="Missing Scan Documentation",
                            category="documentation_readiness",
                            severity="high",
                            financial_impact=tot_charge,
                            affected_lines=[line.get("line_no")],
                            summary="Scan carries a dollar amount but is missing supporting documentation.",
                            why_flagged="Any dollar amount listed for scans must be directly supported with documentation (e.g. invoice or report).",
                            recommended_actions="Request scan report or sublet invoice.",
                            evidence_refs=[{
                                "id": f"ev_{uuid.uuid4().hex[:6]}",
                                "type": "missing",
                                "label": "Scan Report / Invoice",
                                "support_status": "missing",
                                "reason": "Scan line item carries a flat dollar amount requiring an invoice."
                            }]
                        ))
        return results


class CalibrationChargeTimingRule(BaseRule):
    rule_id = "NATGEN_002"
    title = "Calibration Timing"
    category = "carrier_compliance"
    severity = "high"
    
    def applies(self, ctx: AuditContext) -> bool:
        return True
        
    def evaluate(self, ctx: AuditContext) -> List[RuleResult]:
        results = []
        all_lines = ctx.get_all_lines()
        
        for line in all_lines:
            desc = line.get("description", "").lower()
            srv_sub = line.get("service_subtype", "")
            is_calib = srv_sub in ["calibration", "aim", "sensor_aim"] or any(
                w in desc for w in ["calibration", "aim", "target", "adas"]
            ) or ("sensor" in desc and any(kw in desc for kw in ["calibrat", "aim", "adas", "radar"]))
            
            if is_calib:
                fs = line.get("financial_signature", {})
                tot_charge = fs.get("part_price", 0) + fs.get("misc_amount", 0) + fs.get("labor_amount_total", 0)
                supp_id = line.get("supplement", "").upper()
                is_original = (not supp_id) or (supp_id == "E01")
                
                if is_original and tot_charge > 0:
                    results.append(RuleResult(
                        rule_id=self.rule_id,
                        title=self.title,
                        category=self.category,
                        severity=self.severity,
                        financial_impact=tot_charge,
                        affected_lines=[line.get("line_no")],
                        summary="Calibration/Aim procedures should not carry charges on original estimates (E01).",
                        why_flagged="Carrier requires calibration charges to be deferred to supplement phase after scanning.",
                        recommended_actions="Defer to supplement."
                    ))
                elif not is_original and tot_charge > 0:
                    # check for sublet/docs
                    has_docs = False
                    for rl in all_lines:
                        if rl.get("is_sublet", False) or rl.get("row_type") == "sublet":
                            if any(k in rl.get("description", "").lower() for k in ["scan", "calibration", "adas", "report", "invoice"]):
                                has_docs = True
                                break
                    if not has_docs:
                        import uuid
                        scan_doc = next((d for d in ctx.documents if d.get("doc_type") in ["scan_pdf", "invoice"]), None)
                        ev_ref = {}
                        if scan_doc:
                            ev_ref = {
                                "id": f"ev_{uuid.uuid4().hex[:6]}",
                                "type": "scan_pdf",
                                "source_id": scan_doc.get("id"),
                                "label": "Calibration Invoice or Scan PDF",
                                "support_status": "full",
                                "reason": "Calibration supported by document found in evidence matrix.",
                                "url": scan_doc.get("source_url"),
                                "thumbnail_url": scan_doc.get("thumbnail_url"),
                                "is_mock": scan_doc.get("is_mock", False)
                            }
                        else:
                            ev_ref = {
                                "id": f"ev_{uuid.uuid4().hex[:6]}",
                                "type": "missing",
                                "label": "Calibration Invoice or Scan PDF",
                                "support_status": "missing",
                                "reason": "Supplement calibration lacks linked documented support in payload."
                            }
                        
                        results.append(RuleResult(
                            rule_id=self.rule_id,
                            title="Calibration Missing Docs",
                            category="documentation_readiness",
                            severity="medium",
                            financial_impact=tot_charge,
                            affected_lines=[line.get("line_no")],
                            summary="Calibration/Aim billed on supplement without invoice/scan support.",
                            why_flagged="Calibration charges require document/invoice support when requested on supplement.",
                            recommended_actions="Request sublet invoice or scan report.",
                            evidence_refs=[ev_ref]
                        ))
        return results


class CalibrationTriggerSupportRule(BaseRule):
    rule_id = "NATGEN_003"
    title = "Calibration Support Context"
    category = "documentation_readiness"
    severity = "medium"
    
    def applies(self, ctx: AuditContext) -> bool:
        return True
        
    def evaluate(self, ctx: AuditContext) -> List[RuleResult]:
        results = []
        all_lines = ctx.get_all_lines()
        strong_kws = ["bumper", "impact bar", "reinforcement", "grille", "radar", "sensor", "windshield", "camera", "mirror", "module"]
        weak_kws = ["trim", "reflector", "molding", "o/h", "overhaul"]
        
        for line in all_lines:
            desc = line.get("description", "").lower()
            is_calib = line.get("service_subtype") in ["calibration", "aim", "sensor_aim"] or any(
                w in desc for w in ["calibration", "aim", "target", "adas"]
            ) or ("sensor" in desc and any(kw in desc for kw in ["calibrat", "aim", "adas", "radar"]))
            
            if is_calib:
                fs = line.get("financial_signature", {})
                tot_charge = fs.get("part_price", 0) + fs.get("misc_amount", 0) + fs.get("labor_amount_total", 0)
                if tot_charge == 0:
                    continue
                strong_support = False
                weak_support = False
                
                for check_r in all_lines:
                    if check_r.get("line_no") == line.get("line_no"): continue
                    if check_r.get("row_type") in ["operation", "part_only", "part_labor_hybrid", "part_included_labor_hybrid"]:
                        c_desc = f"{check_r.get('description', '')} {check_r.get('operation_label', '')}".lower()
                        if any(kw in c_desc for kw in strong_kws):
                            strong_support = True
                            break
                        elif any(kw in c_desc for kw in weak_kws):
                            weak_support = True
                            
                if not strong_support:
                    supp_id = line.get("supplement", "").upper()
                    is_original = (not supp_id) or (supp_id == "E01")
                    
                    if weak_support:
                        results.append(RuleResult(
                            rule_id=self.rule_id,
                            title=self.title,
                            category=self.category,
                            severity="low",
                            affected_lines=[line.get("line_no")],
                            summary="Calibration/Aim present with limited related trigger support.",
                            why_flagged="Weak trigger parts identified for calibration.",
                            recommended_actions="Verify structural necessity."
                        ))
                    elif is_original:
                        results.append(RuleResult(
                            rule_id=self.rule_id,
                            title="Calibration Violation",
                            category="carrier_compliance",
                            severity="high",
                            affected_lines=[line.get("line_no")],
                            summary="Calibration/Aim billed without related trigger part on original estimate.",
                            why_flagged="No radar/sensor/bumper trigger parts present on estimate sequence.",
                            recommended_actions="Remove unsupported calibration charge."
                        ))
                    else:
                        results.append(RuleResult(
                            rule_id=self.rule_id,
                            title=self.title,
                            category=self.category,
                            severity="medium",
                            affected_lines=[line.get("line_no")],
                            summary="Calibration billed on supplement without clear trigger part.",
                            why_flagged="No clear trigger operation found for supplement calibration charge.",
                            recommended_actions="Request explanation from shop."
                        ))
        return results


# ============================================================================
# NatGen Handbook Rules (v4) — merged from natgen_handbook_rules.py
# NOTE: NATGEN_025 (StateLicenseRequiredRule) removed — identical to STATE_001
# ============================================================================


class OEMPartRestrictionRule(BaseRule):
    """
    NATGEN_004: OEM parts only allowed when BOTH criteria are met:
    (1) Current model year AND (2) Under 15,000 miles.
    If either fails, OEM is inappropriate — flag for alternate parts check.
    """
    rule_id = "NATGEN_004"
    title = "OEM Parts Restriction"
    category = "parts_accuracy"
    severity = "high"

    def applies(self, ctx: AuditContext) -> bool:
        return True

    def evaluate(self, ctx: AuditContext) -> List[RuleResult]:
        results = []
        vehicle = ctx.raw_data.get("claim_meta", {}).get("vehicle", {})
        model_year = vehicle.get("year") or ctx.raw_data.get("claim_meta", {}).get("model_year")
        mileage = vehicle.get("mileage") or ctx.raw_data.get("claim_meta", {}).get("mileage")

        for line in ctx.get_all_lines():
            if line.get("is_header"):
                continue

            part_type = str(line.get("part_type", "")).upper()
            if part_type not in ("OEM", "OES"):
                continue

            part_price = line.get("financial_signature", {}).get("part_price", 0)
            if part_price == 0:
                continue

            issues = []
            if model_year:
                try:
                    import datetime
                    current_year = datetime.datetime.now().year
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
                    title=self.title,
                    category=self.category,
                    severity=self.severity,
                    financial_impact=part_price,
                    affected_lines=[line.get("line_no")],
                    summary=f"OEM part may not qualify — {', '.join(issues)}",
                    why_flagged=(
                        f"NatGen requires both current model year AND under 15,000 miles for OEM parts. "
                        f"Line {line.get('line_no')}: {line.get('description', '')} "
                        f"(Part: {line.get('part_number', '')}, Type: {part_type})"
                    ),
                    recommended_actions="Replace with LKQ recycled, remanufactured, or aftermarket part per NatGen parts hierarchy.",
                    debug_context={
                        "model_year": model_year,
                        "mileage": mileage,
                        "part_type": part_type,
                        "part_number": line.get("part_number"),
                    }
                ))

        return results


class UnjustifiedReplaceRule(BaseRule):
    """
    NATGEN_006: Default to repair. Replace must be justified by severe damage,
    safety concerns, or documented repair impracticality.
    Flags replace operations for common panels: bumper covers, fenders, outer panels.
    """
    rule_id = "NATGEN_006"
    title = "Unjustified Replace Operation"
    category = "line_item_support"
    severity = "medium"
    HIGH_RISK_PANELS = ["bumper", "fender", "door skin", "outer panel", "quarter panel"]

    def applies(self, ctx: AuditContext) -> bool:
        return True

    def evaluate(self, ctx: AuditContext) -> List[RuleResult]:
        results = []
        for line in ctx.get_all_lines():
            if line.get("is_header"):
                continue

            op_label = str(line.get("operation_label", "")).lower()
            desc = str(line.get("description", "")).lower()
            part_type = str(line.get("part_type", "")).upper()

            if op_label not in ("replace",):
                continue

            if "corrosion protection" in desc:
                continue

            is_high_risk = any(kw in desc for kw in self.HIGH_RISK_PANELS)

            if is_high_risk or part_type not in ("OEM", "OES", "PAA", "PAR"):
                results.append(RuleResult(
                    rule_id=self.rule_id,
                    title=self.title,
                    category=self.category,
                    severity=self.severity,
                    affected_lines=[line.get("line_no")],
                    summary=f"Replace operation on {line.get('description', '')} — verify repair is not viable.",
                    why_flagged=(
                        f"NatGen defaults to repair. Replace must be justified by severe damage, "
                        f"safety concern, or documented repair impracticality. "
                        f"Common replace revisions occur on bumper covers, fenders, and outer panels."
                    ),
                    recommended_actions="Verify photos show severe damage. If repairable, change to repair operation.",
                ))

        return results


class UnnecessaryBlendRule(BaseRule):
    """
    NATGEN_007: Avoid blending when color match is likely, panel separation exists,
    or repair area is minimal. Blends must be necessary — not routine.
    """
    rule_id = "NATGEN_007"
    title = "Unnecessary Blend Panel"
    category = "line_item_support"
    severity = "medium"

    def applies(self, ctx: AuditContext) -> bool:
        return True

    def evaluate(self, ctx: AuditContext) -> List[RuleResult]:
        results = []
        for line in ctx.get_all_lines():
            if line.get("is_header"):
                continue

            op_label = str(line.get("operation_label", "")).lower()
            op_code = str(line.get("operation_code", "")).upper()
            desc = str(line.get("description", "")).lower()

            if op_label not in ("blend",) and op_code not in ("BLK", "BLN"):
                continue

            results.append(RuleResult(
                rule_id=self.rule_id,
                title=self.title,
                category=self.category,
                severity=self.severity,
                affected_lines=[line.get("line_no")],
                summary=f"Blend on {line.get('description', '')} — verify necessity.",
                why_flagged=(
                    f"NatGen: avoid blends when color match is likely, panel separation exists, "
                    f"or repair area is minimal. Blends must be necessary — not routine. "
                    f"Unnecessary blends are a HIGH revision trigger."
                ),
                recommended_actions="Verify blend is necessary for color match. If panel separation exists or repair is minimal, remove the blend.",
            ))

        return results


class UnjustifiedRIOperationsRule(BaseRule):
    """
    NATGEN_008: Each R&I line must be justified by repair access, part replacement,
    or refinish necessity. Do not add R&I lines that do not directly support the repair work.
    """
    rule_id = "NATGEN_008"
    title = "Unjustified R&I Operation"
    category = "line_item_support"
    severity = "low"

    def applies(self, ctx: AuditContext) -> bool:
        return True

    def evaluate(self, ctx: AuditContext) -> List[RuleResult]:
        results = []
        all_lines = ctx.get_all_lines()
        
        # Check for PDR context — which panels are being PDR'd
        pdr_panels = set()
        for line in all_lines:
            op = str(line.get("operation_label", "")).lower()
            desc = str(line.get("description", "")).lower()
            if op == "pdr":
                for kw in ["hood", "roof", "fender", "door", "quarter", "deck", "trunk", "lift"]:
                    if kw in desc:
                        pdr_panels.add(kw)

        # On hail claims, ALL R&I is for PDR access — skip entirely
        if pdr_panels:
            return results
        for line in all_lines:
            op = str(line.get("operation_label", "")).lower()
            desc = str(line.get("description", "")).lower()
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

            # PDR context exceptions
            if "insulator" in desc and "hood" in pdr_panels:
                continue
            if "headliner" in desc and "roof" in pdr_panels:
                if "drop" in desc:
                    results.append(RuleResult(
                        rule_id=self.rule_id, title="Headliner Drop — Verify",
                        category=self.category, severity="medium",
                        affected_lines=[line.get("line_no")],
                        summary=f"Headliner DROP on line {line.get('line_no')} — verify justification.",
                        why_flagged="Headliner drop requires documentation. Full headliner removal is more invasive than partial access.",
                        recommended_actions="Verify headliner drop is necessary for roof PDR access. Document in report.",
                    ))
                continue
            if "hood" in desc and "hood" in pdr_panels:
                continue
            if ("lift" in desc or "tail" in desc) and "gate" in desc and "lift" in pdr_panels:
                continue

            cosmetic_ri_keywords = ["handle", "trim", "molding", "nameplate", "emblem", "badge", "wiper"]
            is_cosmetic = any(kw in desc for kw in cosmetic_ri_keywords)

            results.append(RuleResult(
                rule_id=self.rule_id,
                title=self.title,
                category=self.category,
                severity=self.severity if is_cosmetic else "low",
                affected_lines=[line.get("line_no")],
                summary=f"R&I on {line.get('description', '')} — verify repair access justification.",
                why_flagged=(
                    f"NatGen: each R&I must directly support repair access, part replacement, "
                    f"or refinish. R&I lines without clear repair connection will be revised."
                    + (" Cosmetic R&I has higher revision risk." if is_cosmetic else "")
                ),
                recommended_actions="Verify R&I is required for repair access. If not, remove the line.",
            ))

        return results


class ExcessivePaintScopeRule(BaseRule):
    """
    NATGEN_012: Large paint scopes frequently trigger revisions.
    Watch for unnecessary adjacent panel refinish, excess clear coat,
    and unnecessary mask/setup lines.
    """
    rule_id = "NATGEN_012"
    title = "Excessive Paint Scope"
    category = "line_item_support"
    severity = "medium"

    def applies(self, ctx: AuditContext) -> bool:
        return True

    def evaluate(self, ctx: AuditContext) -> List[RuleResult]:
        results = []
        refinish_panels = 0

        for line in ctx.get_all_lines():
            op_label = str(line.get("operation_label", "")).lower()
            labor_refinish = line.get("labor_amount_refinish", 0) or line.get("financial_signature", {}).get("labor_amount_refinish", 0)

            if op_label in ("refinish",) or labor_refinish > 0:
                refinish_panels += 1

        if refinish_panels >= 3:
            first_refinish = next(
                (l for l in ctx.get_all_lines()
                 if str(l.get("operation_label", "")).lower() in ("refinish",)
                 or (l.get("labor_amount_refinish", 0) or l.get("financial_signature", {}).get("labor_amount_refinish", 0)) > 0),
                ctx.get_all_lines()[0] if ctx.get_all_lines() else {}
            )
            results.append(RuleResult(
                rule_id=self.rule_id,
                title=self.title,
                category=self.category,
                severity="high",
                affected_lines=[first_refinish.get("line_no")] if first_refinish else [],
                summary=f"Large paint scope — {refinish_panels} refinish panels detected.",
                why_flagged=(
                    f"NatGen: large paint scopes frequently trigger revisions. "
                    f"{refinish_panels} refinish panels found. Verify adjacent panel refinish "
                    f"is necessary and aligns with actual damage area."
                ),
                recommended_actions="Review paint scope. Remove unnecessary adjacent panel refinish and excess operations.",
            ))

        return results


class ShopInfoRule(BaseRule):
    """
    NATGEN_011: Repair facility info must be complete.
    On supplements: shop info MANDATORY.
    If no shop: must say "Owner's Choice".
    """
    rule_id = "NATGEN_011"
    title = "Shop Information — Verifed?"
    category = "documentation_readiness"
    severity = "high"

    def applies(self, ctx: AuditContext) -> bool:
        return True

    def evaluate(self, ctx: AuditContext) -> List[RuleResult]:
        results = []
        shop = ctx.raw_data.get("claim_meta", {}).get("shop", {})

        name = shop.get("name", "")
        address = shop.get("address", "")
        phone = shop.get("phone", "")

        is_supplement = ctx.is_supplement()

        missing = []
        if not name:
            missing.append("shop name")
        if not address:
            missing.append("shop address")
        if not phone:
            missing.append("phone number")

        if missing:
            choice_kws = ("shop of choice", "owner's choice", "owners choice", "owner choice")
            full_text = (name + " " + address).lower()
            is_choice = any(kw in full_text for kw in choice_kws) or ("owner" in full_text and "choice" in full_text)
            if is_choice:
                pass  # Normal for initial estimates — skip
            elif is_supplement:
                severity = "critical"
                msg = f"SUPPLEMENT — missing shop info: {', '.join(missing)}"
                why = (
                    f"NatGen: ALL supplements MUST have complete shop information. "
                    f"Missing: {', '.join(missing)}. This will cause a revision."
                )
            else:
                severity = "high"
                msg = f"Missing shop info: {', '.join(missing)}"
                why = (
                    f"NatGen requires complete repair facility information. "
                    f"Missing: {', '.join(missing)}. If no repair facility, enter 'Owner\\'s Choice'."
                )

            results.append(RuleResult(
                rule_id=self.rule_id,
                title=self.title,
                category=self.category,
                severity=severity,
                affected_lines=[],
                summary=msg,
                why_flagged=why,
                recommended_actions=(
                    "Fill in shop name, address, and phone. "
                    "If no repair facility is involved, enter 'Owner\\'s Choice'."
                ),
            ))
        elif name and not is_supplement:
            is_choice = any(kw in name.lower() for kw in ("shop of choice", "owner's choice", "owners choice", "owner choice"))
            if is_choice:
                pass
            else:
                results.append(RuleResult(
                    rule_id=self.rule_id,
                    title="Shop Info Present — Confirm",
                    category=self.category,
                    severity="low",
                    affected_lines=[],
                    summary=f"Shop: {name}, {address} — confirm correct before submission.",
                    why_flagged=(
                        f"Shop info extracted from CCC: {name}, {address}. "
                        f"Verify this is correct. NatGen: incomplete shop information "
                        f"is one of the most common revision triggers."
                    ),
                    recommended_actions="Confirm shop details are correct and complete.",
                ))

        return results


class DocumentationRule(BaseRule):
    """
    NATGEN_010: Sublet charges and scans require supporting documentation.
    Every sublet requires a supporting invoice. Dealer mechanical sublets
    must be broken down by operation.
    """
    rule_id = "NATGEN_010"
    title = "Missing Sublet Documentation"
    category = "documentation_readiness"
    severity = "high"

    def applies(self, ctx: AuditContext) -> bool:
        return True

    def evaluate(self, ctx: AuditContext) -> List[RuleResult]:
        results = []
        for line in ctx.get_all_lines():
            if line.get("is_header"):
                continue

            is_sublet = line.get("is_sublet", False)
            row_type = line.get("row_type", "")
            misc_amount = line.get("financial_signature", {}).get("misc_amount", 0)
            desc = str(line.get("description", "")).lower()

            is_scan = "scan" in desc or line.get("service_subtype") == "scan"

            if (is_sublet or row_type == "sublet" or (misc_amount > 50 and not is_scan)) and misc_amount > 0:
                import uuid
                docs = ctx.documents
                has_invoice = any(d.get("doc_type") in ("invoice", "scan_pdf") for d in docs)

                results.append(RuleResult(
                    rule_id=self.rule_id,
                    title=self.title,
                    category=self.category,
                    severity=self.severity,
                    financial_impact=misc_amount,
                    affected_lines=[line.get("line_no")],
                    summary=f"{'Scan' if is_scan else 'Sublet'} charge ${misc_amount:.2f} requires supporting documentation.",
                    why_flagged=(
                        f"NatGen: every {'scan' if is_scan else 'sublet'} charge requires a supporting invoice. "
                        f"Without documentation, the carrier will remove or revise the charge."
                    ),
                    recommended_actions="Attach supporting invoice. Dealer mechanical invoices must be itemized by operation.",
                    evidence_refs=[{
                        "id": f"ev_{uuid.uuid4().hex[:6]}",
                        "type": "invoice",
                        "label": f"{'Scan' if is_scan else 'Sublet'} Invoice",
                        "support_status": "full" if has_invoice else "missing",
                        "reason": "Invoice detected via Vision Mapping" if has_invoice else "Sublet/scan charge requires invoice per NatGen guidelines",
                    }]
                ))

        return results


# ============================================================================
# NatGen Client Guidelines — Additional Rules  
# ============================================================================


class NoBodyShopSuppliesRule(BaseRule):
    """NATGEN_013: Body shop supplies NEVER allowed on NatGen estimates."""
    rule_id = "NATGEN_013"
    title = "Body Shop Supplies Not Allowed"
    category = "carrier_compliance"
    severity = "high"

    def applies(self, ctx: AuditContext) -> bool:
        return True

    def evaluate(self, ctx: AuditContext) -> List[RuleResult]:
        results = []
        for line in ctx.get_all_lines():
            desc = str(line.get("description", "")).lower()
            if "shop supply" in desc or "body supply" in desc:
                results.append(RuleResult(
                    rule_id=self.rule_id, title=self.title, category=self.category,
                    severity=self.severity, affected_lines=[line.get("line_no")],
                    summary="Body shop supplies are never allowed on NatGen estimates.",
                    why_flagged="NatGen: 'Body Shop Supplies are never allowed on an estimate.'",
                    recommended_actions="Remove shop supplies charge immediately.",
                ))
        return results


class NoLKQSuspensionRule(BaseRule):
    """NATGEN_015: No LKQ suspension parts. A/M or OEM only. Engine cradles/cross members/rear axles excepted."""
    rule_id = "NATGEN_015"
    title = "LKQ Suspension Parts Not Permitted"
    category = "parts_accuracy"
    severity = "high"
    _SUSP = ["strut","control arm","ball joint","tie rod","sway bar","trailing arm",
             "steering knuckle","hub","bearing","shock","leaf spring","steering rack",
             "steering box","steering column","drag link","pitman arm","cv joint","axle shaft"]
    _EXCEPT = ["cross member","subframe","engine cradle","rear axle"]

    def applies(self, ctx: AuditContext) -> bool: return True

    def evaluate(self, ctx: AuditContext) -> List[RuleResult]:
        results = []
        for line in ctx.get_all_lines():
            if line.get("is_header"): continue
            pt = str(line.get("part_type","")).upper()
            desc = str(line.get("description","")).lower()
            if pt not in ("PAR","PAM","LKQ","REC"): continue
            if any(kw in desc for kw in self._SUSP) and not any(kw in desc for kw in self._EXCEPT):
                results.append(RuleResult(
                    rule_id=self.rule_id, title=self.title, category=self.category,
                    severity=self.severity, affected_lines=[line.get("line_no")],
                    summary=f"LKQ suspension part: {line.get('description','')}",
                    why_flagged="NatGen prohibits LKQ suspension parts. Use A/M or OEM. Only engine cradles, cross members, and solid rear axle assemblies are LKQ exceptions.",
                    recommended_actions="Replace with A/M or OEM part. Apply betterment on OEM wearable parts.",
                ))
        return results


class HazWasteCapRule(BaseRule):
    """NATGEN_020: Hazardous waste capped at $3.00, negotiated max $5.00."""
    rule_id = "NATGEN_020"
    title = "Hazardous Waste Exceeds Cap"
    category = "carrier_compliance"
    severity = "medium"

    def applies(self, ctx: AuditContext) -> bool: return True

    def evaluate(self, ctx: AuditContext) -> List[RuleResult]:
        results = []
        for line in ctx.get_all_lines():
            desc = str(line.get("description","")).lower()
            if not ("haz" in desc and "waste" in desc) and line.get("misc_subtype") != "hazardous_waste":
                continue
            total = line.get("financial_signature",{}).get("misc_amount",0) + line.get("financial_signature",{}).get("part_price",0)
            if total > 5.00:
                results.append(RuleResult(
                    rule_id=self.rule_id, title=self.title, category=self.category,
                    severity=self.severity, financial_impact=total-5.00,
                    affected_lines=[line.get("line_no")],
                    summary=f"Haz waste ${total:.2f} exceeds NatGen cap of $5.00",
                    why_flagged=f"NatGen caps hazardous waste at $3.00 ($5.00 max negotiation). Current: ${total:.2f}",
                    recommended_actions="Reduce haz waste to $5.00 maximum.",
                ))
        return results


class NoFlexAdditiveRule(BaseRule):
    """NATGEN_014: NO FLEX — flex additive never allowed on NatGen estimates."""
    rule_id = "NATGEN_014"
    title = "Flex Additive Not Allowed"
    category = "carrier_compliance"
    severity = "high"

    def applies(self, ctx: AuditContext) -> bool: return True

    def evaluate(self, ctx: AuditContext) -> List[RuleResult]:
        results = []
        for line in ctx.get_all_lines():
            desc = str(line.get("description","")).lower()
            if line.get("misc_subtype") == "flex_additive" or ("flex" in desc and "add" in desc):
                results.append(RuleResult(
                    rule_id=self.rule_id, title=self.title, category=self.category,
                    severity=self.severity, affected_lines=[line.get("line_no")],
                    summary="Flex additive is never allowed on NatGen estimates.",
                    why_flagged="NatGen client guidelines: 'NO FLEX'. Flex additive charges are prohibited.",
                    recommended_actions="Remove flex additive charge immediately.",
                ))
        return results


class TotalLossWriteFullRule(BaseRule):
    """NATGEN_022: Write 100% of damages — do not stop at total loss threshold."""
    rule_id = "NATGEN_022"
    title = "Total Loss — Write Complete Damages"
    category = "carrier_compliance"
    severity = "medium"

    def applies(self, ctx: AuditContext) -> bool: return True

    def evaluate(self, ctx: AuditContext) -> List[RuleResult]:
        results = []
        total = ctx.total_estimate()
        if total > 7500:
            results.append(RuleResult(
                rule_id=self.rule_id, title=self.title, category=self.category,
                severity="low", affected_lines=[],
                summary=f"Estimate ${total:,.0f} — ensure 100% of damages written per NatGen guidelines.",
                why_flagged="NatGen: 'Do not stop writing damages at T/L threshold. Always write 100% of the damages.'",
                recommended_actions="Verify all damages documented. Include ALL accident-related damage regardless of threshold.",
            ))
        return results


class SafetySystemLKQRule(BaseRule):
    """NATGEN_016: No LKQ on safety systems — seat belts, SRS, steering, suspension, brakes."""
    rule_id = "NATGEN_016"
    title = "LKQ Parts on Safety System"
    category = "parts_accuracy"
    severity = "critical"
    _SAFETY = ["seat belt","srs","airbag","air bag","pretensioner","steering",
               "brake pad","brake rotor","brake caliper","brake line","master cylinder",
               "abs","anti-lock"]

    def applies(self, ctx: AuditContext) -> bool: return True

    def evaluate(self, ctx: AuditContext) -> List[RuleResult]:
        results = []
        for line in ctx.get_all_lines():
            if line.get("is_header"): continue
            pt = str(line.get("part_type","")).upper()
            desc = str(line.get("description","")).lower()
            if pt not in ("PAR","PAM","LKQ","REC"): continue
            if any(kw in desc for kw in self._SAFETY):
                results.append(RuleResult(
                    rule_id=self.rule_id, title=self.title, category=self.category,
                    severity=self.severity, affected_lines=[line.get("line_no")],
                    summary=f"LKQ part on safety system: {line.get('description','')}",
                    why_flagged="NatGen prohibits LKQ on safety systems (seat belts, SRS, steering, suspension, brakes). Use A/M or OEM.",
                    recommended_actions="Replace with A/M or OEM part. Safety-critical violation.",
                ))
        return results
