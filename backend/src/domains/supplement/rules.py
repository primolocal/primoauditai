"""Supplement Documentation Rules — invoice requirements for calibrations,
scans, wheel alignments, and sublet on supplement estimates.
"""
from __future__ import annotations

from src.engine.base import BaseRule, RuleResult
from src.engine.context import AuditContext


class AlternativePartsVerificationRule(BaseRule):
    """SUPP_001: Verify alternative parts on supplement lines meet carrier hierarchy."""
    rule_id = "SUPP_001"
    category = "parts_accuracy"
    severity = "high"
    ALT = ["lkq", "a/m", "aftermarket", "recycled", "recon", "capa", "opt oe"]

    def applies(self, ctx: AuditContext) -> bool:
        return any("supplement" in str(line.get("description", "")).lower() or line.get("supplement") for line in ctx.lines)

    def evaluate(self, ctx: AuditContext) -> list[RuleResult]:
        results = []
        for line in ctx.lines:
            if line.get("is_header"):
                continue
            desc = str(line.get("description", "")).lower()
            pt = str(line.get("part_type", "")).upper()
            pn = str(line.get("part_number", ""))
            supp = str(line.get("supplement", ""))
            op = str(line.get("operation", ""))
            if not supp or supp == "E01":
                continue
            if not pn and not any(kw in desc for kw in self.ALT):
                continue
            if op in ("Included", "") and "delete" in desc:
                continue
            # Only flag if part type or keywords indicate alternative part
            is_alt = any(kw in desc for kw in self.ALT) or pt in ("LKQ", "PAR", "PAM", "PAA", "REC")
            if not is_alt:
                continue
            cat = "unknown"
            if "lkq" in desc or pt in ("LKQ", "PAR", "PAM"):
                cat = "LKQ/Recycled"
            elif "a/m" in desc or "aftermarket" in desc or pt in ("PAA",):
                cat = "Aftermarket"
            elif "capa" in desc:
                cat = "CAPA Certified"
            elif "recon" in desc or pt in ("REC",):
                cat = "Reconditioned"
            has_markup = "+25%" in desc
            results.append(RuleResult(
                rule_id=self.rule_id,
                category=self.category,
                severity=self.severity,
                description=f"Supplement line {line.get('line_no')} uses {cat} part — verify sourcing.",
                line_numbers=[int(line.get("line_no", 0))],
            ))
        return results


class SupplementCalibrationDocRule(BaseRule):
    """SUPP_002: Calibrations on supplements require supporting invoice documentation."""
    rule_id = "SUPP_002"
    category = "documentation_readiness"
    severity = "high"

    def applies(self, ctx: AuditContext) -> bool:
        return any("supplement" in str(line.get("description", "")).lower() or line.get("supplement") for line in ctx.lines)

    def evaluate(self, ctx: AuditContext) -> list[RuleResult]:
        results = []
        for line in ctx.lines:
            if line.get("is_header"):
                continue
            desc = str(line.get("description", "")).lower()
            supp = str(line.get("supplement", ""))
            if not supp or supp == "E01":
                continue
            if not any(kw in desc for kw in ["calibration", "aim", "adas", "radar", "target"]):
                continue
            pp = line.get("part_price", 0) or 0
            lh = line.get("labor_hours", 0) or 0
            ph = line.get("paint_hours", 0) or 0
            tot = pp + lh * 50 + ph * 50
            if tot == 0:
                continue
            results.append(RuleResult(
                rule_id=self.rule_id,
                category=self.category,
                severity=self.severity,
                description=f"Calibration on supplement line {line.get('line_no')} requires supporting invoice.",
                line_numbers=[int(line.get("line_no", 0))],
            ))
        return results


class SupplementScanDocRule(BaseRule):
    """SUPP_003: Scan charges beyond 0.5 allowance require invoice on supplements."""
    rule_id = "SUPP_003"
    category = "documentation_readiness"
    severity = "high"

    def applies(self, ctx: AuditContext) -> bool:
        return any("supplement" in str(line.get("description", "")).lower() or line.get("supplement") for line in ctx.lines)

    def evaluate(self, ctx: AuditContext) -> list[RuleResult]:
        results = []
        for line in ctx.lines:
            if line.get("is_header"):
                continue
            desc = str(line.get("description", "")).lower()
            supp = str(line.get("supplement", ""))
            if not supp or supp == "E01":
                continue
            if "scan" not in desc:
                continue
            lh = line.get("labor_hours", 0) or 0
            pp = line.get("part_price", 0) or 0
            if lh <= 0.5 and pp == 0:
                continue
            results.append(RuleResult(
                rule_id=self.rule_id,
                category=self.category,
                severity=self.severity,
                description=f"Scan charge on supplement line {line.get('line_no')} requires invoice.",
                line_numbers=[int(line.get("line_no", 0))],
            ))
        return results


class SupplementAlignmentDocRule(BaseRule):
    """SUPP_004: Wheel alignments on supplements require invoice documentation."""
    rule_id = "SUPP_004"
    category = "documentation_readiness"
    severity = "high"

    def applies(self, ctx: AuditContext) -> bool:
        return any("supplement" in str(line.get("description", "")).lower() or line.get("supplement") for line in ctx.lines)

    def evaluate(self, ctx: AuditContext) -> list[RuleResult]:
        results = []
        for line in ctx.lines:
            if line.get("is_header"):
                continue
            desc = str(line.get("description", "")).lower()
            supp = str(line.get("supplement", ""))
            if not supp or supp == "E01":
                continue
            if not any(kw in desc for kw in ["alignment", "align", "wheel align", "front end align", "4 wheel align", "thrust align"]):
                continue
            pp = line.get("part_price", 0) or 0
            lh = line.get("labor_hours", 0) or 0
            ph = line.get("paint_hours", 0) or 0
            tot = pp + lh * 50 + ph * 50
            if tot == 0:
                continue
            results.append(RuleResult(
                rule_id=self.rule_id,
                category=self.category,
                severity=self.severity,
                description=f"Wheel alignment on supplement line {line.get('line_no')} requires invoice.",
                line_numbers=[int(line.get("line_no", 0))],
            ))
        return results


class SupplementSubletDocRule(BaseRule):
    """SUPP_005: ANY sublet on a supplement requires supporting invoice."""
    rule_id = "SUPP_005"
    category = "documentation_readiness"
    severity = "high"

    def applies(self, ctx: AuditContext) -> bool:
        return any("supplement" in str(line.get("description", "")).lower() or line.get("supplement") for line in ctx.lines)

    def evaluate(self, ctx: AuditContext) -> list[RuleResult]:
        results = []
        for line in ctx.lines:
            if line.get("is_header"):
                continue
            supp = str(line.get("supplement", ""))
            if not supp or supp == "E01":
                continue
            desc = str(line.get("description", "")).lower()
            is_sublet = line.get("is_sublet", False) or line.get("row_type") == "sublet"
            has_kw = any(kw in desc for kw in ["sublet", "subl", "tow", "storage", "glass", "alignment", "align", "calibration", "scan", "pdr", "dent", "hail"])
            if not is_sublet and not has_kw:
                continue
            pp = line.get("part_price", 0) or 0
            lh = line.get("labor_hours", 0) or 0
            ph = line.get("paint_hours", 0) or 0
            tot = pp + lh * 50 + ph * 50
            if tot == 0:
                continue
            results.append(RuleResult(
                rule_id=self.rule_id,
                category=self.category,
                severity=self.severity,
                description=f"Sublet on supplement line {line.get('line_no')} requires supporting invoice.",
                line_numbers=[int(line.get("line_no", 0))],
            ))
        return results
