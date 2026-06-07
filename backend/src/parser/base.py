"""
Parser base — shared utilities for all parsers.
"""
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.engine.context import AuditContext


@dataclass
class ParsedEstimate:
    """Normalized output from any parser."""
    lines: list[dict[str, Any]] = field(default_factory=list)
    panels: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    documents: list[dict[str, Any]] = field(default_factory=list)
    extracted_photos: list[dict[str, Any]] = field(default_factory=list)

    def to_audit_context(self) -> "AuditContext":
        """Convert to AuditContext for rules engine."""
        from src.engine.context import AuditContext
        return AuditContext(
            lines=self.lines,
            panels=self.panels,
            metadata=self.metadata,
            documents=self.documents,
            extracted_photos=self.extracted_photos,
        )


def extract_zip_from_address(address: str) -> str | None:
    """Extract 5-digit ZIP from address string."""
    match = re.search(r"\b(\d{5})(?:-\d{4})?\b", address)
    return match.group(1) if match else None


def extract_state_from_address(address: str) -> str | None:
    """Extract 2-letter state abbreviation from address."""
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
