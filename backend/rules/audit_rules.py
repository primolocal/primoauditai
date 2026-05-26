from typing import List
from audit_context import AuditContext
from rules.base import BaseRule, RuleResult

class IncludedLaborRule(BaseRule):
    rule_id = "AUDIT_001"
    title = "Included Labor Anomaly"
    category = "documentation_readiness"
    severity = "medium"
    
    def applies(self, ctx: AuditContext) -> bool:
        return True
        
    def evaluate(self, ctx: AuditContext) -> List[RuleResult]:
        results = []
        for line in ctx.get_all_lines():
            fs = line.get("financial_signature", {})
            p_price = fs.get("part_price", 0)
            l_amt = fs.get("labor_amount_total", 0)
            l_hrs = fs.get("labor_hours_total", 0)
            
            op_type = line.get("operation_type", "")
            op_code = line.get("operation_code", "")
            pt_typ = line.get("part_type", "")
            
            # Identify purely structural bundled operations where labor pays out via formula (or inherently $0)
            exempt_operations = ["Included", "Blend", "Refinish", "Overhaul", "Clear Coat"]
            is_exempt = op_type in exempt_operations or op_code in ["INC", "BLK", "BLN", "REF", "REFN", "O/H"]
            
            # The rule "hours but no labor amount" ONLY fires if:
            # - labor hours > 0
            # - total billed amount (part + labor + misc) is 0
            # - operation_type does not justify bundled or flat pricing
            
            misc_amt = fs.get("misc_amount", 0)
            total_billed_amount = p_price + l_amt + misc_amt
            
            if l_hrs > 0 and total_billed_amount == 0 and not is_exempt:
                results.append(RuleResult(
                    rule_id=self.rule_id,
                    title=self.title,
                    category=self.category,
                    severity=self.severity,
                    financial_impact=0.0,
                    affected_lines=[line.get("line_no")],
                    summary="Part billed with hours but no labor amount.",
                    why_flagged=f"Line {line.get('line_no')} (Op: {op_type or 'Unknown'}) maps {l_hrs} hours to $0.00 total billed amount without a recognized bundled pricing structure.",
                    recommended_actions="Verify included labor overlaps with other operations or correct the rate.",
                    debug_context={
                        "labor_hours": l_hrs,
                        "line_total_amount": total_billed_amount,
                        "operation_type": op_type,
                        "operation_code": op_code,
                        "part_type": pt_typ,
                        "p_price": p_price,
                        "is_exempt_evaluated": is_exempt
                    }
                ))
        return results

class HighMiscRule(BaseRule):
    rule_id = "AUDIT_004"
    title = "High Miscellaneous Charge"
    category = "line_item_support"
    severity = "medium"
    
    def applies(self, ctx: AuditContext) -> bool:
        return True
        
    def evaluate(self, ctx: AuditContext) -> List[RuleResult]:
        results = []
        for line in ctx.get_all_lines():
            m_amt = line.get("financial_signature", {}).get("misc_amount", 0)
            if line.get("row_type") == "misc_only" and m_amt > 50:
                import uuid
                
                # Check Evidence Matrix for invoice
                invoice_doc = next((d for d in ctx.documents if d.get("doc_type") == "invoice"), None)
                ev_ref = {}
                if invoice_doc:
                    ev_ref = {
                         "id": f"ev_{uuid.uuid4().hex[:6]}",
                         "type": "invoice",
                         "source_id": invoice_doc.get("id"),
                         "label": "Sublet Invoice",
                         "support_status": "full",
                         "reason": "Invoice detected via Vision Mapping matching the misc amount.",
                         "url": invoice_doc.get("source_url"),
                         "thumbnail_url": invoice_doc.get("thumbnail_url"),
                         "is_mock": invoice_doc.get("is_mock", False)
                    }
                else:
                    ev_ref = {
                         "id": f"ev_{uuid.uuid4().hex[:6]}",
                         "type": "invoice",
                         "label": "Sublet Invoice",
                         "support_status": "missing",
                         "reason": "Charges exceeding $50 require a formal linked invoice."
                    }
                
                results.append(RuleResult(
                    rule_id=self.rule_id,
                    title=self.title,
                    category=self.category,
                    severity=self.severity,
                    financial_impact=m_amt,
                    affected_lines=[line.get("line_no")],
                    summary="Misc charge >$50 requires invoice/review.",
                    why_flagged=f"Line {line.get('line_no')} contains an unstructured miscellaneous charge of ${m_amt:.2f}.",
                    recommended_actions="Request Sublet Invoice to support the charge.",
                    evidence_refs=[ev_ref]
                ))
        return results

class HazWasteRule(BaseRule):
    rule_id = "AUDIT_005"
    title = "Hazardous Waste Charge"
    category = "carrier_compliance"
    severity = "low"
    
    def applies(self, ctx: AuditContext) -> bool:
        return True
        
    def evaluate(self, ctx: AuditContext) -> List[RuleResult]:
        results = []
        for line in ctx.get_all_lines():
            desc = line.get("description", "").lower()
            if line.get("misc_subtype") == "hazardous_waste" or ("haz" in desc and "waste" in desc):
                results.append(RuleResult(
                    rule_id=self.rule_id,
                    title=self.title,
                    category=self.category,
                    severity=self.severity,
                    affected_lines=[line.get("line_no")],
                    summary="Hazardous waste detected.",
                    why_flagged="Hazardous waste charge flagged for carrier allowance check.",
                    recommended_actions="Verify carrier allowance logic allows direct line item bill for haz waste."
                ))
        return results

class FlexAddRule(BaseRule):
    rule_id = "AUDIT_006"
    title = "Flex Additive Charge"
    category = "line_item_support"
    severity = "low"
    
    def applies(self, ctx: AuditContext) -> bool:
        return True
        
    def evaluate(self, ctx: AuditContext) -> List[RuleResult]:
        results = []
        for line in ctx.get_all_lines():
            desc = line.get("description", "").lower()
            if line.get("misc_subtype") == "flex_additive" or ("flex" in desc and "add" in desc):
                results.append(RuleResult(
                    rule_id=self.rule_id,
                    title=self.title,
                    category=self.category,
                    severity=self.severity,
                    affected_lines=[line.get("line_no")],
                    summary="Flex additive detected.",
                    why_flagged="Flex additive charge. Applicability on painted panel requires verification.",
                    recommended_actions="Verify applicability on panel."
                ))
        return results

class NegativeLaborRule(BaseRule):
    rule_id = "AUDIT_007"
    title = "Negative Labor Adjustment"
    category = "carrier_compliance"
    severity = "high"

    # Legitimate CCC operations that produce negative values
    _LEGIT_NEGATIVE = [
        "overlap", "deduction", "deduct", "discount", "reduction",
        "credit", "less", "adjustment", "adj", "negotiated"
    ]

    def applies(self, ctx: AuditContext) -> bool:
        return True
        
    def evaluate(self, ctx: AuditContext) -> List[RuleResult]:
        results = []
        for line in ctx.get_all_lines():
            fs = line.get("financial_signature", {})
            if fs.get("labor_amount_total", 0) < 0 or fs.get("labor_hours_total", 0) < 0:
                desc = str(line.get("description", "")).lower()
                op_label = str(line.get("operation_label", "")).lower()
                op_code = str(line.get("operation_code", "")).lower()

                # Skip legitimate CCC overlap/deduction lines
                if any(kw in desc for kw in self._LEGIT_NEGATIVE):
                    continue
                if any(kw in op_label for kw in self._LEGIT_NEGATIVE):
                    continue
                if op_code in ("ovl", "ded", "adj", "dsc"):
                    continue

                # Only flag truly suspicious negative labor
                # Small adjustments (< $25) are usually fine
                neg_amount = fs.get("labor_amount_total", 0)
                neg_hours = fs.get("labor_hours_total", 0)
                if neg_amount < 0 and abs(neg_amount) < 25:
                    continue

                results.append(RuleResult(
                    rule_id=self.rule_id,
                    title=self.title,
                    category=self.category,
                    severity=self.severity,
                    affected_lines=[line.get("line_no")],
                    summary=f"Unexplained negative labor: ${neg_amount:.2f} / {neg_hours} hrs",
                    why_flagged=(
                        f"Line {line.get('line_no')} has negative labor (${neg_amount:.2f}) "
                        f"that doesn't appear to be a standard overlap deduction or reduction. "
                        f"Standard CCC overlap and deduction lines are automatically excluded."
                    ),
                    recommended_actions=(
                        "If this is a legitimate overlap/discount: no action needed. "
                        "If this is a manual negative entry: reject and correct."
                    ),
                ))
        return results

class LaborNoHoursRule(BaseRule):
    rule_id = "AUDIT_008"
    title = "Labor Amount Without Hours"
    category = "labor_reasonableness"
    severity = "high"

    # CCC flat-rate operations that legitimately have $ but no hours
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
            desc = line.get("description", "").lower()
            op_label = line.get("operation_label", "")

            if not (fs.get("labor_amount_total", 0) > 0 and fs.get("labor_hours_total", 0) == 0):
                continue

            # Skip scans (already handled by NATGEN_001)
            if "scan" in desc:
                continue

            # Skip CCC flat-rate operations — these legitimately have $0 hours
            if any(kw in desc for kw in self._FLAT_RATE):
                continue
            if op_label == "" and not line.get("operation_code"):
                # No operation specified — likely a flat-rate or misc line
                if fs.get("labor_amount_total", 0) < 100:
                    continue

            results.append(RuleResult(
                rule_id=self.rule_id,
                title=self.title,
                category=self.category,
                severity=self.severity,
                financial_impact=fs.get("labor_amount_total", 0),
                affected_lines=[line.get("line_no")],
                summary=f"Labor \${fs.get('labor_amount_total',0):.2f} billed without hours on {line.get('description','')}",
                why_flagged=(
                    f"A labor charge of \${fs.get('labor_amount_total',0):.2f} was made "
                    f"without underlying hourly justification. Standard CCC flat-rate "
                    f"operations (transport, prime/block, corrosion protection, etc.) are excluded."
                ),
                recommended_actions="If this is hourly labor, add the hours. If flat-rate, ignore.",
            ))
        return results

class ZeroPricePartRule(BaseRule):
    rule_id = "AUDIT_009"
    title = "Zero-Price Part"
    category = "parts_accuracy"
    severity = "low"
    
    def applies(self, ctx: AuditContext) -> bool:
        return True
        
    def evaluate(self, ctx: AuditContext) -> List[RuleResult]:
        results = []
        for line in ctx.get_all_lines():
            h_pno = bool(line.get("part_number"))
            is_inc = line.get("is_included_labor", False)
            fs = line.get("financial_signature", {})
            p_price = fs.get("part_price", 0)
            m_amt = fs.get("misc_amount", 0)
            r_type = line.get("row_type", "")
            
            if h_pno and p_price == 0 and m_amt == 0 and not is_inc and r_type in ["part_only", "part_labor_hybrid", "part_included_labor_hybrid"]:
                results.append(RuleResult(
                    rule_id=self.rule_id,
                    title=self.title,
                    category=self.category,
                    severity=self.severity,
                    affected_lines=[line.get("line_no")],
                    summary="Zero-price part detected.",
                    why_flagged="Part exists but has $0 price logic attached, likely manually overridden.",
                    recommended_actions="Review justification for zero entry."
                ))
        return results

class MechOnCosmeticRule(BaseRule):
    rule_id = "AUDIT_010"
    title = "Mechanical Labor on Cosmetic File"
    category = "labor_reasonableness"
    severity = "medium"
    
    def applies(self, ctx: AuditContext) -> bool:
        return True
        
    def evaluate(self, ctx: AuditContext) -> List[RuleResult]:
        has_structural = False
        for line in ctx.get_all_lines():
            if line.get("labor_amount_frame", 0) > 0 or line.get("labor_amount_diag", 0) > 0:
                has_structural = True
                break
                
        results = []
        if not has_structural:
            for line in ctx.get_all_lines():
                if line.get("labor_amount_mechanical", 0) > 0 or line.get("labor_amount_diag", 0) > 0:
                    results.append(RuleResult(
                        rule_id=self.rule_id,
                        title=self.title,
                        category=self.category,
                        severity=self.severity,
                        financial_impact=line.get("labor_amount_mechanical", 0),
                        affected_lines=[line.get("line_no")],
                        summary="Mechanical/Diagnostic labor on presumed cosmetic estimate.",
                        why_flagged="The file has no structural damage, yet mechanical/diag labor is billed.",
                        recommended_actions="Confirm mechanical operations are tied to direct impact."
                    ))
        return results
