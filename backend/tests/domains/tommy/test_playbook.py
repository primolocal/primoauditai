"""
Tests for the Communication Playbook.
"""
import pytest

from src.domains.tommy.playbook import format_comment, RETURN_COMMENTS, PROHIBITED_ALTERNATIVES


class TestPlaybookTemplates:
    """Verify all 15 templates are present and format correctly."""

    def test_scan_invoice_missing(self) -> None:
        result = format_comment("scan_invoice_missing", line=42)
        assert "line 42" in result
        assert "scan invoices" in result

    def test_dealer_invoice_lump(self) -> None:
        result = format_comment("dealer_invoice_lump")
        assert "itemize" in result
        assert "CCC labor lines" in result

    def test_oem_not_supported(self) -> None:
        result = format_comment("oem_not_supported", part="hood", year=2022, mileage="34K")
        assert "hood" in result
        assert "2022" in result
        assert "34K" in result

    def test_safe_harbor_fallback(self) -> None:
        result = format_comment("safe_harbor", concern="this is correct")
        assert "It does not appear that this is correct" in result

    def test_missing_key_uses_safe_harbor(self) -> None:
        """Unknown template key falls back to safe_harbor."""
        result = format_comment("nonexistent_key")
        assert "review and adjust" in result

    def test_all_templates_present(self) -> None:
        expected_keys = [
            "replace_not_supported", "oem_not_supported", "blend_not_supported",
            "sublet_invoice_missing", "scan_invoice_missing", "dealer_invoice_lump",
            "photos_insufficient", "shop_info_missing", "nada_missing",
            "deductible_missing", "hail_photos_no_board", "pdr_markup_verify",
            "hail_roof_at_residence", "safe_harbor", "general_review",
            "review_and_revise", "clarify_rationale", "escalate_to_manager",
        ]
        for key in expected_keys:
            assert key in RETURN_COMMENTS, f"Missing template: {key}"

    def test_prohibited_alternatives_present(self) -> None:
        assert "Remove this / Delete operation" in PROHIBITED_ALTERNATIVES
        assert "Do not pay / We're not paying that" in PROHIBITED_ALTERNATIVES
