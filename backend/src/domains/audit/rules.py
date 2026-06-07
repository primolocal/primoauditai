"""
Core audit rules (AUDIT_001, AUDIT_004-010).
These detect fundamental estimate issues: included labor, misc charges,
haz waste, flex additive, negative labor, labor without hours, zero-price parts,
and mechanical labor on cosmetic estimates.
"""
from typing import List

from src.engine.base import BaseRule, RuleResult
from src.engine.context import AuditContext


class IncludedLaborRule(BaseRule):
    """AUDIT_001: Included Labor Anomaly. Hours without labor amount on non-exempt operations."""
    rule_id = "AUDIT_001"
    category = "documentation_readiness"
    description = "Part billed with hours but no labor amount"
    severity = "medium"

    # Operations where $0 labor amount is expected
    _EXEMPT_OPS = ["Included", "Blend", "Refinish", "Overhaul", "Clear Coat"]
    _EXEMPT_CODES = ["INC", "BLK", "BLN", "REF", "REFN", "O/H"]

    def applies(self, ctx: AuditContext) -> bool:
        return True

    def evaluate(self, ctx: AuditContext) -> List[RuleResult]:
        results = []
        for line in ctx.get_all_lines():
            fs = line.get("financial_signature", {})
            l_hrs = fs.get("labor_hours_total", 0)
            l_amt = fs.get("labor_amount_total", 0)
            p_price = fs.get("part_price", 0)
            m_amt = fs.get("misc_amount", 0)
            total_billed = p_price + l_amt + m_amt

            op_type = str(line.get("operation_type", ""))
            op_code = str(line.get("operation_code", ""))
            is_exempt = (
                op_type in self._EXEMPT_OPS
                or op_code in self._EXEMPT_CODES
            )

            if l_hrs > 0 and total_billed == 0 and not is_exempt:
                results.append(RuleResult(
                    rule_id=self.rule_id,
                    category=self.category,
                    severity=self.severity,
                    description=self.description,
                    line_numbers=[line.get("line_no")],
                    summary=f"Line {line.get('line_no')} has {l_hrs} hours but $0 total billed.",
                    detail=f"Operation '{op_type or 'Unknown'}' maps {l_hrs} hours to $0 without a recognized bundled pricing structure.",
                    action="Verify included labor overlaps or correct the rate.",
                ))
        return results


class HighMiscRule(BaseRule):
    """AUDIT_004: High Miscellaneous Charge >$50."""
    rule_id = "AUDIT_004"
    category = "line_item_support"
    description = "Misc charge exceeding $50 requires invoice/review"
    severity = "medium"

    def applies(self, ctx: AuditContext) -> bool:
        return True

    def evaluate(self, ctx: AuditContext) -> List[RuleResult]:
        results = []
        for line in ctx.get_all_lines():
            m_amt = line.get("financial_signature", {}).get("misc_amount", 0)
            if line.get("row_type") == "misc_only" and m_amt > 50:
                results.append(RuleResult(
                    rule_id=self.rule_id,
                    category=self.category,
                    severity=self.severity,
                    description=self.description,
                    line_numbers=[line.get("line_no")],
                    summary=f"Misc charge ${m_amt:.2f} on line {line.get('line_no')} requires invoice.",
                    detail=f"Unstructured miscellaneous charge of ${m_amt:.2f}. Sublet invoice required for charges >$50.",
                    action="Request sublet invoice to support the charge.",
                ))
        return results


class HazWasteRule(BaseRule):
    """AUDIT_005: Hazardous Waste Charge."""
    rule_id = "AUDIT_005"
    category = "carrier_compliance"
    description = "Hazardous waste charge flagged for carrier allowance check"
    severity = "low"

    def applies(self, ctx: AuditContext) -> bool:
        return True

    def evaluate(self, ctx: AuditContext) -> List[RuleResult]:
        results = []
        for line in ctx.get_all_lines():
            desc = str(line.get("description", "")).lower()
            if line.get("misc_subtype") == "hazardous_waste" or ("haz" in desc and "waste" in desc):
                results.append(RuleResult(
                    rule_id=self.rule_id,
                    category=self.category,
                    severity=self.severity,
                    description=self.description,
                    line_numbers=[line.get("line_no")],
                    summary="Hazardous waste charge detected.",
                    detail="Hazardous waste charge flagged for carrier allowance check.",
                    action="Verify carrier allows direct line-item bill for haz waste.",
                ))
        return results


class FlexAddRule(BaseRule):
    """AUDIT_006: Flex Additive Charge."""
    rule_id = "AUDIT_006"
    category = "line_item_support"
    description = "Flex additive charge — verify applicability on panel"
    severity = "low"

    def applies(self, ctx: AuditContext) -> bool:
        return True

    def evaluate(self, ctx: AuditContext) -> List[RuleResult]:
        results = []
        for line in ctx.get_all_lines():
            desc = str(line.get("description", "")).lower()
            if line.get("misc_subtype") == "flex_additive" or ("flex" in desc and "add" in desc):
                results.append(RuleResult(
                    rule_id=self.rule_id,
                    category=self.category,
                    severity=self.severity,
                    description=self.description,
                    line_numbers=[line.get("line_no")],
                    summary="Flex additive detected.",
                    detail="Flex additive charge. Applicability on painted panel requires verification.",
                    action="Verify applicability on panel.",
                ))
        return results


class NegativeLaborRule(BaseRule):
    """AUDIT_007: Negative Labor Adjustment.
    Skips legitimate CCC overlap/deduction/reduction lines.
    """
    rule_id = "AUDIT_007"
    category = "carrier_compliance"
    description = "Unexplained negative labor adjustment"
    severity = "high"

    _LEGIT_NEGATIVE = [
        "overlap", "deduction", "deduct", "discount", "reduction",
        "credit", "less", "adjustment", "adj", "negotiated",
    ]
    _LEGIT_CODES = ["ovl", "ded", "adj", "dsc"]

    def applies(self, ctx: AuditContext) -> bool:
        return True

    def evaluate(self, ctx: AuditContext) -> List[RuleResult]:
        results = []
        for line in ctx.get_all_lines():
            fs = line.get("financial_signature", {})
            l_amt = fs.get("labor_amount_total", 0)
            l_hrs = fs.get("labor_hours_total", 0)
            if l_amt >= 0 and l_hrs >= 0:
                continue

            desc = str(line.get("description", "")).lower()
            op_label = str(line.get("operation_label", "")).lower()
            op_code = str(line.get("operation_code", "")).lower()

            # Skip legitimate CCC overlap/deduction lines
            if any(kw in desc for kw in self._LEGIT_NEGATIVE):
                continue
            if any(kw in op_label for kw in self._LEGIT_NEGATIVE):
                continue
            if op_code in self._LEGIT_CODES:
                continue

            # Skip small adjustments (< $25)
            if l_amt < 0 and abs(l_amt) < 25:
                continue

            results.append(RuleResult(
                rule_id=self.rule_id,
                category=self.category,
                severity=self.severity,
                description=self.description,
                line_numbers=[line.get("line_no")],
                summary=f"Unexplained negative labor: ${l_amt:.2f} / {l_hrs} hrs",
                detail=f"Line {line.get('line_no')} has negative labor (${l_amt:.2f}) not matching standard overlap/deduction patterns.",
                action="If legitimate overlap: no action. If manual negative entry: reject and correct.",
            ))
        return results


class LaborNoHoursRule(BaseRule):
    """AUDIT_008: Labor Amount Without Hours.
    Skips CCC flat-rate operations that legitimately have $ but no hours.
    """
    rule_id = "AUDIT_008"
    category = "labor_reasonableness"
    description = "Labor charge billed without underlying hourly justification"
    severity = "high"

    _FLAT_RATE = [
        "prime and block", "clear bra", "mud guard", "transport",
        "corrosion protection", "safety inspection", "denib", "tint",
        "polish", "buff", "detail", "wash", "clean", "mask",
        "cover car", "flex additive", "haz", "waste", "supply",
        "shop supply", "material", "sundries", "miscellaneous",
    ]

    def applies(self, ctx: AuditContext) -> bool:
        return True

    def evaluate(self, ctx: AuditContext) -> List[RuleResult]:
        results = []
        for line in ctx.get_all_lines():
            fs = line.get("financial_signature", {})
            l_amt = fs.get("labor_amount_total", 0)
            l_hrs = fs.get("labor_hours_total", 0)
            if not (l_amt > 0 and l_hrs == 0):
                continue

            desc = str(line.get("description", "")).lower()
            op_label = str(line.get("operation_label", ""))

            # Skip scans (handled by NATGEN_001)
            if "scan" in desc:
                continue

            # Skip flat-rate operations
            if any(kw in desc for kw in self._FLAT_RATE):
                continue

            # No operation specified + small amount = likely flat-rate
            if not op_label and not line.get("operation_code") and l_amt < 100:
                continue

            results.append(RuleResult(
                rule_id=self.rule_id,
                category=self.category,
                severity=self.severity,
                description=self.description,
                line_numbers=[line.get("line_no")],
                summary=f"Labor ${l_amt:.2f} without hours on '{line.get('description', '')}'",
                detail=f"A labor charge of ${l_amt:.2f} has no underlying hourly justification. Standard CCC flat-rate operations are excluded.",
                action="If hourly labor: add hours. If flat-rate: ignore.",
            ))
        return results


class ZeroPricePartRule(BaseRule):
    """AUDIT_009: Zero-Price Part."""
    rule_id = "AUDIT_009"
    category = "parts_accuracy"
    description = "Part exists but has $0 price — likely manually overridden"
    severity = "low"

    def applies(self, ctx: AuditContext) -> bool:
        return True

    def evaluate(self, ctx: AuditContext) -> List[RuleResult]:
        results = []
        for line in ctx.get_all_lines():
            has_pno = bool(line.get("part_number"))
            is_inc = line.get("is_included_labor", False)
            fs = line.get("financial_signature", {})
            p_price = fs.get("part_price", 0)
            m_amt = fs.get("misc_amount", 0)
            r_type = line.get("row_type", "")

            valid_rows = ["part_only", "part_labor_hybrid", "part_included_labor_hybrid"]
            if has_pno and p_price == 0 and m_amt == 0 and not is_inc and r_type in valid_rows:
                results.append(RuleResult(
                    rule_id=self.rule_id,
                    category=self.category,
                    severity=self.severity,
                    description=self.description,
                    line_numbers=[line.get("line_no")],
                    summary="Zero-price part detected.",
                    detail="Part exists but has $0 price logic, likely manually overridden.",
                    action="Review justification for zero-price entry.",
                ))
        return results


class MechOnCosmeticRule(BaseRule):
    """AUDIT_010: Mechanical Labor on Cosmetic Estimate.
    No structural/frame/diag damage → cosmetic. Mechanical labor then is suspicious.
    """
    rule_id = "AUDIT_010"
    category = "labor_reasonableness"
    description = "Mechanical/diagnostic labor on estimate with no structural damage"
    severity = "medium"

    def applies(self, ctx: AuditContext) -> bool:
        return True

    def evaluate(self, ctx: AuditContext) -> List[RuleResult]:
        has_structural = any(
            line.get("labor_amount_frame", 0) > 0
            or line.get("labor_amount_diag", 0) > 0
            for line in ctx.get_all_lines()
        )
        if has_structural:
            return []

        results = []
        for line in ctx.get_all_lines():
            if line.get("labor_amount_mechanical", 0) > 0 or line.get("labor_amount_diag", 0) > 0:
                results.append(RuleResult(
                    rule_id=self.rule_id,
                    category=self.category,
                    severity=self.severity,
                    description=self.description,
                    line_numbers=[line.get("line_no")],
                    summary="Mechanical/diagnostic labor on presumed cosmetic estimate.",
                    detail="No structural damage detected, yet mechanical/diagnostic labor is billed.",
                    action="Confirm mechanical operations are tied to direct impact.",
                ))
        return results
