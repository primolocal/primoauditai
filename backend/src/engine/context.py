"""
AuditContext — the shared data object passed to every rule.
Wraps parsed estimate data and provides shared helpers.
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class AuditContext:
    """
    The shared context for all rule evaluations.

    Built from a parsed estimate file. Passed to BaseRule.applies()
    and BaseRule.evaluate().

    Attributes:
        lines: Flat list of all estimate line items
        panels: Dict of panel_name -> list of lines for that panel
        metadata: Estimate metadata (shop info, claim info, etc.)
        documents: List of attached document metadata
        extracted_photos: List of photo metadata objects
    """
    lines: List[Dict[str, Any]] = field(default_factory=list)
    panels: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    documents: List[Dict[str, Any]] = field(default_factory=list)
    extracted_photos: List[Dict[str, Any]] = field(default_factory=list)

    # --- Shared helpers (ported from v1 audit_context.py) ---

    def get_all_lines(self) -> List[Dict[str, Any]]:
        """Return flat list of all line items."""
        return self.lines

    def get_lines_by_panel(self, panel_name: str) -> List[Dict[str, Any]]:
        """Return lines for a specific panel."""
        return self.panels.get(panel_name, [])

    def is_hail_claim(self) -> bool:
        """Detect hail/PDR claims from loss description."""
        loss_desc = str(self.metadata.get("loss_description", "")).lower()
        return any(
            word in loss_desc
            for word in ["hail", "dent", "pdr", "paintless", "storm", "weather"]
        )

    def is_supplement(self) -> bool:
        """Detect supplement estimates from document type."""
        doc_type = str(self.metadata.get("document_type", "")).lower()
        return "supplement" in doc_type or "supp" in doc_type

    def total_estimate(self) -> float:
        """Sum all line totals."""
        return sum(
            float(line.get("total", 0) or line.get("amount", 0) or 0)
            for line in self.lines
        )

    def total_labor(self) -> float:
        """Sum all labor hours."""
        return sum(
            float(line.get("labor_hours", 0) or 0)
            for line in self.lines
        )

    def total_parts(self) -> float:
        """Sum all parts totals."""
        return sum(
            float(line.get("parts_total", 0) or 0)
            for line in self.lines
        )

    def shop_state(self) -> Optional[str]:
        """Extract state abbreviation from shop address."""
        address = str(self.metadata.get("shop_address", "")).upper()
        # Common state abbreviations near end of address line
        states = [
            "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
            "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
            "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
            "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
            "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
            "DC", "PR",
        ]
        for state in states:
            if f", {state} " in address or address.endswith(f", {state}"):
                return state
        return None

    def shop_zip(self) -> Optional[str]:
        """Extract ZIP code from shop address."""
        address = str(self.metadata.get("shop_address", ""))
        # Simple 5-digit ZIP extraction
        import re
        match = re.search(r"\b(\d{5})(?:-\d{4})?\b", address)
        return match.group(1) if match else None

    def carrier(self) -> Optional[str]:
        """Return carrier name from metadata."""
        return self.metadata.get("insurance_company") or self.metadata.get("carrier")

    def line_descriptions(self) -> List[str]:
        """Return all line descriptions (lowercased) for pattern matching."""
        return [
            str(line.get("description", "")).lower()
            for line in self.lines
        ]

    def lines_matching(self, pattern: str) -> List[Dict[str, Any]]:
        """Return lines where description contains pattern (case-insensitive)."""
        pattern = pattern.lower()
        return [
            line for line in self.lines
            if pattern in str(line.get("description", "")).lower()
        ]

    def __repr__(self) -> str:
        return f"<AuditContext lines={len(self.lines)} panels={len(self.panels)}>"
