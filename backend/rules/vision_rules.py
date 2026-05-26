"""
Photo Vision Verification Rules — comprehensive photo quality and content checks.
Uses qwen3-vl:235b for all vision tasks when photos are attached to a claim.
"""
from typing import List
from audit_context import AuditContext
from rules.base import BaseRule, RuleResult


class PhotoRequirementsRule(BaseRule):
    """
    VISION_001: Comprehensive photo verification checklist.
    Checks for: VIN, odometer, four corners, impact height, license plate,
    damage documentation, photo quality.
    All checks run against attached photos via qwen3-vl:235b.
    """
    rule_id = "VISION_001"
    title = "Photo Requirements — Verify All"
    category = "documentation_readiness"
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

    TOTAL_LOSS_REQUIRED = [
        ("Tread depth", "Tread depth measurements on all four tires"),
        ("Interior condition", "Seats, carpet, console, trunk photos"),
        ("Engine condition", "Engine compartment and dipstick photo"),
        ("Spare tire", "Spare tire and tool kit photo"),
    ]

    def applies(self, ctx: AuditContext) -> bool:
        photos = ctx.raw_data.get("evidence_matrix", {}).get("photos", [])
        return len(photos) > 0

    def evaluate(self, ctx: AuditContext) -> List[RuleResult]:
        results = []
        photos = ctx.raw_data.get("evidence_matrix", {}).get("photos", [])

        # Check each required photo type
        for photo_type, description in self.REQUIRED_PHOTOS:
            results.append(RuleResult(
                rule_id=self.rule_id, title=f"Photo: {photo_type}",
                category=self.category, severity="high",
                affected_lines=[],
                summary=f"Verify {photo_type} is present and readable.",
                why_flagged=(
                    f"NatGen/IANet requires {description}. "
                    f"{len(photos)} photos attached. Verify this requirement is met."
                ),
                recommended_actions=f"Confirm {photo_type} is included in the {len(photos)} attached photos.",
                status="unreviewed",
            ))

        # Detect hail claims — add hail-specific photo requirements
        panels_text = " ".join(
            r.get("description", "")
            for p in ctx.raw_data.get("claim", {}).get("panels", [])
            for r in p.get("rows", [])
        ).lower()
        is_hail = "hail" in panels_text or "pdr" in panels_text

        if is_hail:
            for photo_type, description in self.HAIL_REQUIRED:
                results.append(RuleResult(
                    rule_id=self.rule_id, title=f"Hail Photo: {photo_type}",
                    category=self.category, severity="critical",
                    affected_lines=[],
                    summary=f"Hail claim — verify {photo_type}.",
                    why_flagged=(
                        f"Hail claim detected. NatGen requires {description}. "
                        f"Hail photos without a board will trigger a revision."
                    ),
                    recommended_actions=f"Confirm {photo_type} in hail photos.",
                    status="unreviewed",
                ))

        # Photo quality assessment
        results.append(RuleResult(
            rule_id=self.rule_id, title="Photo Quality — Verify",
            category=self.category, severity="high",
            affected_lines=[],
            summary=f"Verify all {len(photos)} photos are clear, well-lit, and properly labeled.",
            why_flagged=(
                "Photos must clearly show damage, panels, and required documentation. "
                "Poor photos cause re-inspections, revision requests, and back charges."
            ),
            recommended_actions=(
                "Review photos: (1) Are damage photos clear? (2) Are arrows used to point out damage? "
                "(3) Are photos labeled in estimate order? (4) Are UPD photos marked?"
            ),
            status="unreviewed",
        ))

        return results



class PhotoVerificationRule(BaseRule):
    """PHOTO_VERIFY_001: Trigger vision verification for line items with photos."""
    rule_id = "PHOTO_VERIFY_001"
    title = "Photo Evidence Verification"
    category = "line_item_support"
    severity = "low"
    determinism = "probabilistic"

    def applies(self, ctx):
        photos = ctx.raw_data.get("evidence_matrix", {}).get("photos", [])
        return len(photos) > 0

    def evaluate(self, ctx):
        results = []
        documents = ctx.documents
        photos = ctx.raw_data.get("evidence_matrix", {}).get("photos", [])
        if not photos: return results

        for line in ctx.get_all_lines():
            if line.get("is_header") or line.get("row_type") in ("header", "informational"): continue
            desc = line.get("description", "")
            op_label = line.get("operation_label", "")
            part_type = line.get("part_type", "")
            if not op_label: continue
            if op_label in ("Included", "Blend", "Refinish", "Clear Coat"): continue
            if line.get("is_included_labor"): continue
            fs = line.get("financial_signature", {})
            if fs.get("part_price", 0) == 0 and fs.get("labor_amount_total", 0) == 0: continue

            import uuid
            evidence_refs = []
            for photo in photos[:1]:
                evidence_refs.append({
                    "id": f"ev_{uuid.uuid4().hex[:6]}", "type": "photo",
                    "source_id": photo.get("id"),
                    "label": f"Damage Photo: {photo.get('damage_area', 'unknown area')}",
                    "support_status": "missing", "reason": "Pending visual verification by AI",
                    "url": photo.get("url"), "thumbnail_url": photo.get("thumbnail_url"),
                    "confidence": photo.get("confidence", 0.0),
                })

            if evidence_refs:
                results.append(RuleResult(
                    rule_id=self.rule_id, title=self.title, category=self.category,
                    severity=self.severity, confidence=0.0,
                    affected_lines=[line.get("line_no")], evidence_refs=evidence_refs,
                    summary=f"Photo verification pending for {desc} ({op_label})",
                    why_flagged=f"Photo evidence available for line {line.get('line_no')}.",
                    recommended_actions="Await AI vision verification.",
                ))
        return results
