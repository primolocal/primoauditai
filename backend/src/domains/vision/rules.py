"""Photo Vision Verification Rules — comprehensive photo quality and content checks.
Uses qwen3-vl:235b for all vision tasks when photos are attached to a claim.
"""
from __future__ import annotations

from src.engine.base import BaseRule, RuleResult
from src.engine.context import AuditContext


class PhotoRequirementsRule(BaseRule):
    """VISION_001: Comprehensive photo verification checklist."""
    rule_id = "VISION_001"
    category = "documentation_readiness"
    description = "Verify required photos are present: VIN, odometer, four corners, license plate, damage, production date, prior damage"
    severity = "high"

    REQUIRED_PHOTOS = [
        ("VIN photo (dashboard)", "VIN photo from dashboard or door jamb"),
        ("Odometer photo", "Odometer reading or alternative documentation"),
        ("Four corners", "Clear photos of all four corners of the vehicle"),
        ("License plate", "License plate photo"),
        ("Damage panel photos", "Photos of each damaged panel following estimate order"),
        ("Production date label", "Production date label photo"),
        ("Prior damage photos", "Unrelated prior damage photos clearly marked as UPD"),
    ]

    HAIL_REQUIRED = [
        ("Striped/checker board", "All hail photos must use striped board or checker board"),
        ("Dent visibility", "Dents must be clearly visible in hail photos"),
    ]

    def applies(self, ctx: AuditContext) -> bool:
        return len(ctx.extracted_photos) > 0

    def evaluate(self, ctx: AuditContext) -> list[RuleResult]:
        results = []
        photos = ctx.extracted_photos
        photo_count = len(photos)

        for photo_type, description in self.REQUIRED_PHOTOS:
            results.append(RuleResult(
                rule_id=self.rule_id,
                category=self.category,
                severity=self.severity,
                description=f"Verify {photo_type} is present and readable.",
                line_numbers=[],
                summary=f"Verify {photo_type} is present and readable.",
                detail=(
                    f"NatGen/IANet requires {description}. "
                    f"{photo_count} photos attached. Verify this requirement is met."
                ),
                action=f"Confirm {photo_type} is included in the {photo_count} attached photos.",
            ))

        # Hail claims add hail-specific photo requirements
        if ctx.is_hail_claim():
            for photo_type, description in self.HAIL_REQUIRED:
                results.append(RuleResult(
                    rule_id=self.rule_id,
                    category=self.category,
                    severity="critical",
                    description=f"Hail claim — verify {photo_type}.",
                    line_numbers=[],
                    summary=f"Hail claim — verify {photo_type}.",
                    detail=(
                        f"Hail claim detected. NatGen requires {description}. "
                        f"Hail photos without a board will trigger a revision."
                    ),
                    action=f"Confirm {photo_type} in hail photos.",
                ))

        # Photo quality assessment
        results.append(RuleResult(
            rule_id=self.rule_id,
            category=self.category,
            severity="high",
            description=f"Verify all {photo_count} photos are clear, well-lit, and properly labeled.",
            line_numbers=[],
            summary=f"Verify all {photo_count} photos are clear, well-lit, and properly labeled.",
            detail=(
                "Photos must clearly show damage, panels, and required documentation. "
                "Poor photos cause re-inspections, revision requests, and back charges."
            ),
            action=(
                "Review photos: (1) Are damage photos clear? (2) Are arrows used? "
                "(3) Are photos labeled in estimate order? (4) Are UPD photos marked?"
            ),
        ))

        return results


class PhotoVerificationRule(BaseRule):
    """PHOTO_VERIFY_001: Trigger vision verification for line items with photos."""
    rule_id = "PHOTO_VERIFY_001"
    category = "line_item_support"
    description = "Photo evidence verification for estimate lines"
    severity = "low"

    def applies(self, ctx: AuditContext) -> bool:
        return len(ctx.extracted_photos) > 0

    def evaluate(self, ctx: AuditContext) -> list[RuleResult]:
        results = []
        photos = ctx.extracted_photos
        if not photos:
            return results

        for line in ctx.get_all_lines():
            if line.get("is_header"):
                continue
            desc = str(line.get("description", ""))
            op_label = str(line.get("operation_label", "")).lower()
            if not op_label:
                continue
            if op_label in ("included", "blend", "refinish", "clear coat"):
                continue
            if line.get("is_included_labor"):
                continue
            fs = line.get("financial_signature", {})
            if fs.get("part_price", 0) == 0 and fs.get("labor_amount_total", 0) == 0:
                continue

            if photos:
                results.append(RuleResult(
                    rule_id=self.rule_id,
                    category=self.category,
                    severity=self.severity,
                    description=f"Photo verification pending for {desc} ({op_label})",
                    line_numbers=[line.get("line_no") or 0],
                    summary=f"Photo verification pending for {desc} ({op_label})",
                    detail=f"Photo evidence available for line {line.get('line_no')}.",
                    action="Await AI vision verification.",
                    confidence=0.0,
                ))

        return results


class VisionAnalysisRule(BaseRule):
    """VISION_ANALYSIS_001: Run AI vision analysis on all damage photos."""
    rule_id = "VISION_ANALYSIS_001"
    category = "line_item_support"
    description = "AI vision analysis for damage detection and line item matching"
    severity = "low"

    def applies(self, ctx: AuditContext) -> bool:
        photos = ctx.extracted_photos
        if not photos:
            return False
        return not any(p.get("ai_damage_type") for p in photos)

    def evaluate(self, ctx: AuditContext) -> list[RuleResult]:
        photos = ctx.extracted_photos
        if not photos:
            return []

        # Stub: vision analysis service not wired in v2 yet
        return [RuleResult(
            rule_id=self.rule_id,
            category=self.category,
            severity=self.severity,
            description=f"AI vision analysis pending for {len(photos)} photos.",
            line_numbers=[],
            summary=f"AI vision analysis pending for {len(photos)} photos.",
            detail="Vision AI not yet wired in v2. Enable vision pipeline for full analysis.",
            action="Enable vision pipeline for damage detection and line item matching.",
        )]
