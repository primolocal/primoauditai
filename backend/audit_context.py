from typing import Any, Dict, List

class AuditContext:
    def __init__(self, raw_data: Dict[str, Any]):
        self.raw_data = raw_data
        
    @property
    def panels(self) -> List[Dict[str, Any]]:
        return self.raw_data.get("claim", {}).get("panels", [])
        
    def get_all_lines(self) -> List[Dict[str, Any]]:
        lines = []
        for p in self.panels:
            lines.extend(p.get("rows", []))
        return lines
        
    @property
    def validation_counts(self) -> Dict[str, int]:
        return self.raw_data.get("claim", {}).get("validation", {})
        
    @property
    def documents(self) -> List[Dict[str, Any]]:
        return self.raw_data.get("evidence_matrix", {}).get("documents", [])

    # ----------------------------------------------------------------
    # Convenience methods — replaces repeated inline pattern-matching
    # across rules and API code.
    # ----------------------------------------------------------------

    def is_hail_claim(self) -> bool:
        """Scan all line descriptions for 'hail' or 'pdr' keywords."""
        panels_text = " ".join(
            r.get("description", "") or ""
            for p in self.raw_data.get("claim", {}).get("panels", [])
            for r in p.get("rows", [])
        ).lower()
        return "hail" in panels_text or "pdr" in panels_text

    def is_supplement(self) -> bool:
        """True if any row has a supplement label other than empty or E01."""
        for panel in self.raw_data.get("claim", {}).get("panels", []):
            for row in panel.get("rows", []):
                supp = str(row.get("supplement", "")).upper()
                if supp and supp not in ("", "E01"):
                    return True
        return False

    def total_estimate(self) -> float:
        """Sum of (part_price + labor_amount_total + misc_amount) across all lines."""
        return sum(
            line.get("financial_signature", {}).get("part_price", 0) +
            line.get("financial_signature", {}).get("labor_amount_total", 0) +
            line.get("financial_signature", {}).get("misc_amount", 0)
            for line in self.get_all_lines()
        )

    def shop_state(self) -> str:
        """Extract state code from claim_meta -> shop -> state, or '' if unavailable."""
        shop = self.raw_data.get("claim_meta", {}).get("shop", {})
        return str(shop.get("state", "")).upper().strip()
