"""
Supplement Documentation Rules — invoice requirements for calibrations,
scans, and wheel alignments on supplement estimates.
"""
from typing import List
import uuid
from audit_context import AuditContext
from rules.base import BaseRule, RuleResult


class SupplementCalibrationDocRule(BaseRule):
    """
    SUPP_002: Calibrations on supplements require supporting invoice documentation.
    """
    rule_id = "SUPP_002"
    title = "Calibration — Invoice Required on Supplement"
    category = "documentation_readiness"
    severity = "high"

    def applies(self, ctx: AuditContext) -> bool:
        return True

    def evaluate(self, ctx: AuditContext) -> List[RuleResult]:
        results = []
        for line in ctx.get_all_lines():
            if line.get("is_header"):
                continue

            desc = str(line.get("description", "")).lower()
            supplement = str(line.get("supplement", ""))

            # Only supplement lines
            if not supplement or supplement == "E01":
                continue

            # Check for calibration keywords
            is_calib = any(kw in desc for kw in ["calibration", "aim", "adas", "radar", "target"])
            if not is_calib:
                continue

            fs = line.get("financial_signature", {})
            tot_charge = fs.get("part_price", 0) + fs.get("misc_amount", 0) + fs.get("labor_amount_total", 0)
            if tot_charge == 0:
                continue

            # Check for invoice in evidence
            docs = ctx.documents
            has_invoice = any(d.get("doc_type") in ("invoice", "scan_pdf") for d in docs)

            results.append(RuleResult(
                rule_id=self.rule_id, title=self.title,
                category=self.category, severity=self.severity,
                financial_impact=tot_charge,
                affected_lines=[line.get("line_no")],
                summary=f"Supplement calibration on line {line.get('line_no')} — invoice required.",
                why_flagged=(
                    f"Calibration on supplement line {line.get('line_no')} "
                    f"(${tot_charge:.2f}). NatGen requires supporting invoice "
                    f"for all calibration charges on supplements."
                ),
                recommended_actions="Attach calibration invoice. If no invoice exists, remove the charge.",
                evidence_refs=[{
                    "id": f"ev_{uuid.uuid4().hex[:6]}",
                    "type": "invoice",
                    "label": "Calibration Invoice",
                    "support_status": "full" if has_invoice else "missing",
                    "reason": "Calibration on supplement requires invoice per NatGen guidelines.",
                }]
            ))

        return results


class SupplementScanDocRule(BaseRule):
    """
    SUPP_003: Scan charges beyond 0.5 allowance or with dollar amounts
    require invoice documentation on supplements.
    """
    rule_id = "SUPP_003"
    title = "Scan Charge — Invoice Required"
    category = "documentation_readiness"
    severity = "high"

    def applies(self, ctx: AuditContext) -> bool:
        return True

    def evaluate(self, ctx: AuditContext) -> List[RuleResult]:
        results = []
        for line in ctx.get_all_lines():
            if line.get("is_header"):
                continue

            desc = str(line.get("description", "")).lower()
            supplement = str(line.get("supplement", ""))

            if not supplement or supplement == "E01":
                continue

            if "scan" not in desc:
                continue

            fs = line.get("financial_signature", {})
            l_hrs = fs.get("labor_hours_total", 0)
            tot_charge = fs.get("part_price", 0) + fs.get("misc_amount", 0)

            # Flag if: over 0.5 hrs OR has any dollar amount
            if l_hrs <= 0.5 and tot_charge == 0:
                continue

            docs = ctx.documents
            has_invoice = any(d.get("doc_type") in ("invoice", "scan_pdf") for d in docs)

            if l_hrs > 0.5:
                summary = (
                    f"Scan at {l_hrs} hrs on line {line.get('line_no')} "
                    f"exceeds 0.5 allowance — invoice required."
                )
            else:
                summary = (
                    f"Scan charge ${tot_charge:.2f} on line {line.get('line_no')} "
                    f"— invoice required."
                )

            results.append(RuleResult(
                rule_id=self.rule_id, title=self.title,
                category=self.category, severity=self.severity,
                financial_impact=tot_charge or (l_hrs * 50),
                affected_lines=[line.get("line_no")],
                summary=summary,
                why_flagged=(
                    f"Scan on supplement line {line.get('line_no')} "
                    + (f"at {l_hrs} hrs (max 0.5). " if l_hrs > 0.5 else f"with ${tot_charge:.2f} charge. ")
                    + "NatGen requires supporting invoice for all scan charges."
                ),
                recommended_actions="Attach scan invoice. If no invoice, remove or reduce charge to 0.5 allowance.",
                evidence_refs=[{
                    "id": f"ev_{uuid.uuid4().hex[:6]}",
                    "type": "scan_pdf",
                    "label": "Scan Invoice",
                    "support_status": "full" if has_invoice else "missing",
                    "reason": "Scan charge requires invoice per NatGen guidelines.",
                }]
            ))

        return results


class SupplementAlignmentDocRule(BaseRule):
    """
    SUPP_004: Wheel alignments on supplements require invoice documentation.
    """
    rule_id = "SUPP_004"
    title = "Wheel Alignment — Invoice Required on Supplement"
    category = "documentation_readiness"
    severity = "high"

    def applies(self, ctx: AuditContext) -> bool:
        return True

    def evaluate(self, ctx: AuditContext) -> List[RuleResult]:
        results = []
        for line in ctx.get_all_lines():
            if line.get("is_header"):
                continue

            desc = str(line.get("description", "")).lower()
            supplement = str(line.get("supplement", ""))

            if not supplement or supplement == "E01":
                continue

            # Check for alignment keywords
            is_alignment = any(kw in desc for kw in [
                "alignment", "align", "wheel align", "front end align",
                "4 wheel align", "thrust align"
            ])
            if not is_alignment:
                continue

            fs = line.get("financial_signature", {})
            tot_charge = fs.get("part_price", 0) + fs.get("misc_amount", 0) + fs.get("labor_amount_total", 0)

            docs = ctx.documents
            has_invoice = any(d.get("doc_type") in ("invoice",) for d in docs)

            results.append(RuleResult(
                rule_id=self.rule_id, title=self.title,
                category=self.category, severity=self.severity,
                financial_impact=tot_charge,
                affected_lines=[line.get("line_no")],
                summary=f"Wheel alignment on supplement line {line.get('line_no')} — invoice required.",
                why_flagged=(
                    f"Wheel alignment on supplement line {line.get('line_no')} "
                    f"(${tot_charge:.2f}). NatGen requires supporting invoice "
                    f"for all alignment charges."
                ),
                recommended_actions="Attach alignment invoice. If no invoice, remove the charge.",
                evidence_refs=[{
                    "id": f"ev_{uuid.uuid4().hex[:6]}",
                    "type": "invoice",
                    "label": "Alignment Invoice",
                    "support_status": "full" if has_invoice else "missing",
                    "reason": "Wheel alignment on supplement requires invoice per NatGen guidelines.",
                }]
            ))

        return results



class AlternativePartsVerificationRule(BaseRule):
    """SUPP_001: Verify alternative parts on supplement lines meet NatGen hierarchy."""
    rule_id = "SUPP_001"
    title = "Alternative Parts — Verify Sourcing"
    category = "parts_accuracy"
    severity = "high"
    ALT = ["lkq", "a/m", "aftermarket", "recycled", "recon", "capa", "opt oe"]

    def applies(self, ctx): return True

    def evaluate(self, ctx):
        results = []
        for line in ctx.get_all_lines():
            if line.get("is_header"): continue
            desc = str(line.get("description", "")).lower()
            pt = str(line.get("part_type", "")).upper()
            pn = str(line.get("part_number", ""))
            supp = str(line.get("supplement", ""))
            op = str(line.get("operation_label", ""))
            if not supp: continue
            if not pn and not any(kw in desc for kw in self.ALT): continue
            if op in ("Included", "") and "delete" in desc: continue
            cat = "unknown"
            if "lkq" in desc or pt in ("LKQ","PAR","PAM"): cat = "LKQ/Recycled"
            elif "a/m" in desc or "aftermarket" in desc or pt in ("PAA",): cat = "Aftermarket"
            elif "capa" in desc: cat = "CAPA Certified"
            elif "recon" in desc or pt in ("REC",): cat = "Reconditioned"
            has_markup = "+25%" in desc
            results.append(RuleResult(
                rule_id=self.rule_id, title=self.title, category=self.category,
                severity=self.severity, affected_lines=[line.get("line_no")],
                summary=f"{cat} part: {line.get('description', '')[:60]}",
                why_flagged=(
                    f"Supplement line {line.get('line_no')} uses {cat} part (#{pn}). "
                    "Verify against NatGen parts hierarchy: LKQ -> Reman -> Aftermarket. "
                    + ("Markup detected — verify justification." if has_markup else "")
                    + " Document 3 parts sources and car-part.com search in report."
                ),
                recommended_actions=(
                    "1. Confirm part meets NatGen guidelines. "
                    "2. Verify car-part.com search completed. "
                    "3. Document 3 parts sources. "
                    + ("4. Verify markup." if has_markup else "")
                ),
            ))
        return results



class SupplementSubletDocRule(BaseRule):
    """SUPP_005: ANY sublet on a supplement requires supporting invoice."""
    rule_id = "SUPP_005"
    title = "Sublet on Supplement — Invoice Required"
    category = "documentation_readiness"
    severity = "high"

    def applies(self, ctx): return True

    def evaluate(self, ctx):
        results = []
        for line in ctx.get_all_lines():
            if line.get("is_header"): continue
            supp = str(line.get("supplement", ""))
            if not supp or supp == "E01": continue

            desc = str(line.get("description", "")).lower()
            is_sublet = line.get("is_sublet", False) or line.get("row_type") == "sublet"
            has_sublet_kw = any(kw in desc for kw in [
                "sublet", "subl", "tow", "storage", "glass",
                "alignment", "align", "calibration", "scan",
                "pdr", "dent", "hail"
            ])
            if not is_sublet and not has_sublet_kw: continue

            fs = line.get("financial_signature", {})
            tot = fs.get("part_price", 0) + fs.get("misc_amount", 0) + fs.get("labor_amount_total", 0)
            if tot == 0: continue

            docs = ctx.documents
            has_invoice = any(d.get("doc_type") in ("invoice", "scan_pdf") for d in docs)

            results.append(RuleResult(
                rule_id=self.rule_id, title=self.title, category=self.category,
                severity=self.severity, financial_impact=tot,
                affected_lines=[line.get("line_no")],
                summary=f"Sublet on supplement L{line.get('line_no')}: {line.get('description','')[:50]} — invoice required.",
                why_flagged=(
                    f"Sublet on supplement line {line.get('line_no')} (${tot:.2f}). "
                    "NatGen: EVERY sublet charge requires a supporting invoice. "
                    "Without documentation, the carrier will remove or revise the charge."
                ),
                recommended_actions="Attach supporting invoice. Dealer invoices must be itemized by operation.",
                evidence_refs=[{
                    "id": f"ev_{uuid.uuid4().hex[:6]}",
                    "type": "invoice",
                    "label": "Sublet Invoice",
                    "support_status": "full" if has_invoice else "missing",
                    "reason": "Sublet on supplement requires invoice per NatGen guidelines.",
                }]
            ))
        return results
