"""
Reference data for QC verification — labor rates and tax rates by ZIP/state.
Data sources: CCC/Mitchell prevailing rate surveys, Tax Foundation 2024.

To update: edit the LABOR_RATES and TAX_RATES dicts below.
"""

from typing import Any

# ── Labor Rates (per hour, by state) ──
# Source: CCC/Mitchell prevailing body labor rate surveys 2024
# Ranges typically $48-78/hr. These are state averages.
LABOR_RATES: dict[str, dict[str, Any]] = {
    "AL": {"default": 55.00},
    "AK": {"default": 78.00},
    "AZ": {"default": 68.00, "zips": {"85001": 70.00}},
    "AR": {"default": 54.00},
    "CA": {"default": 78.00, "zips": {"90001": 82.00, "94101": 85.00, "92101": 80.00}},
    "CO": {"default": 68.00, "zips": {"80201": 72.00}},
    "CT": {"default": 72.00},
    "DE": {"default": 68.00},
    "FL": {"default": 62.00, "zips": {"33101": 65.00, "32801": 60.00}},
    "GA": {"default": 60.00, "zips": {"30301": 65.00}},
    "HI": {"default": 78.00},
    "ID": {"default": 58.00},
    "IL": {"default": 70.00, "zips": {"60015": 72.00, "60601": 75.00}},
    "IN": {"default": 60.00},
    "IA": {"default": 56.00},
    "KS": {"default": 58.00},
    "KY": {"default": 56.00},
    "LA": {"default": 58.00},
    "ME": {"default": 62.00},
    "MD": {"default": 70.00, "zips": {"21201": 72.00}},
    "MA": {"default": 72.00, "zips": {"02101": 75.00}},
    "MI": {"default": 65.00, "zips": {"48201": 68.00}},
    "MN": {"default": 65.00, "zips": {"55401": 68.00}},
    "MS": {"default": 52.00},
    "MO": {"default": 58.00, "zips": {"64772": 55.00, "63101": 62.00}},
    "MT": {"default": 65.00, "zips": {"59714": 65.00}},
    "NE": {"default": 56.00},
    "NV": {"default": 68.00, "zips": {"89101": 70.00}},
    "NH": {"default": 65.00},
    "NJ": {"default": 75.00},
    "NM": {"default": 55.00},
    "NY": {"default": 78.00, "zips": {"10001": 85.00, "14201": 72.00}},
    "NC": {"default": 58.00, "zips": {"28201": 62.00}},
    "ND": {"default": 55.00},
    "OH": {"default": 62.00, "zips": {"44101": 65.00, "43201": 60.00}},
    "OK": {"default": 55.00},
    "OR": {"default": 68.00, "zips": {"97201": 70.00}},
    "PA": {"default": 65.00, "zips": {"19101": 70.00, "15201": 62.00}},
    "RI": {"default": 70.00},
    "SC": {"default": 55.00},
    "SD": {"default": 54.00},
    "TN": {"default": 58.00, "zips": {"37201": 62.00}},
    "TX": {
        "default": 62.00,
        "zips": {
            "76009": 68.00, "76028": 65.00, "75001": 66.00,
            "75201": 70.00, "77001": 72.00, "78701": 68.00, "78201": 65.00,
        },
    },
    "UT": {"default": 60.00},
    "VT": {"default": 62.00},
    "VA": {"default": 65.00, "zips": {"23201": 62.00, "20101": 70.00}},
    "WA": {"default": 72.00, "zips": {"98101": 75.00}},
    "WV": {"default": 55.00},
    "WI": {"default": 60.00, "zips": {"53201": 62.00}},
    "WY": {"default": 56.00},
    "DC": {"default": 75.00},
}

# ── Tax Rates (combined state + local sales tax, by state) ──
# Source: Tax Foundation 2024 — average combined rates
TAX_RATES: dict[str, dict[str, Any]] = {
    "AL": {"default": 0.0900},
    "AK": {"default": 0.0176},   # No state tax, local only
    "AZ": {"default": 0.0840, "zips": {"85001": 0.0860}},
    "AR": {"default": 0.0947},
    "CA": {"default": 0.0885, "zips": {"90001": 0.1025, "94101": 0.0875, "92101": 0.0775}},
    "CO": {"default": 0.0790, "zips": {"80201": 0.0881}},
    "CT": {"default": 0.0635},
    "DE": {"default": 0.0000},   # No sales tax
    "FL": {"default": 0.0702, "zips": {"33101": 0.0700, "32801": 0.0650}},
    "GA": {"default": 0.0740, "zips": {"30301": 0.0890}},
    "HI": {"default": 0.0444},
    "ID": {"default": 0.0603},
    "IL": {"default": 0.0886, "zips": {"60015": 0.0700, "60601": 0.1025}},
    "IN": {"default": 0.0700},
    "IA": {"default": 0.0694},
    "KS": {"default": 0.0870},
    "KY": {"default": 0.0600},
    "LA": {"default": 0.0955},
    "ME": {"default": 0.0550},
    "MD": {"default": 0.0600},
    "MA": {"default": 0.0625},
    "MI": {"default": 0.0600},
    "MN": {"default": 0.0779, "zips": {"55401": 0.0803}},
    "MS": {"default": 0.0707},
    "MO": {"default": 0.0833, "zips": {"64772": 0.05725, "63101": 0.0968}},
    "MT": {"default": 0.0000},   # No sales tax
    "NE": {"default": 0.0694},
    "NV": {"default": 0.0823, "zips": {"89101": 0.0838}},
    "NH": {"default": 0.0000},   # No sales tax
    "NJ": {"default": 0.0660},
    "NM": {"default": 0.0767},
    "NY": {"default": 0.0852, "zips": {"10001": 0.08875, "14201": 0.0875}},
    "NC": {"default": 0.0699},
    "ND": {"default": 0.0685},
    "OH": {"default": 0.0724, "zips": {"44101": 0.0800, "43201": 0.0750}},
    "OK": {"default": 0.0891},
    "OR": {"default": 0.0000},   # No sales tax
    "PA": {"default": 0.0634, "zips": {"19101": 0.0800, "15201": 0.0700}},
    "RI": {"default": 0.0700},
    "SC": {"default": 0.0744},
    "SD": {"default": 0.0640},
    "TN": {"default": 0.0955, "zips": {"37201": 0.0925}},
    "TX": {
        "default": 0.0820,
        "zips": {
            "76009": 0.0825, "76028": 0.0825, "75001": 0.0825,
            "75201": 0.0825, "77001": 0.0825, "78701": 0.0825, "78201": 0.0825,
        },
    },
    "UT": {"default": 0.0719},
    "VT": {"default": 0.0627},
    "VA": {"default": 0.0575, "zips": {"20101": 0.0600}},
    "WA": {"default": 0.0929, "zips": {"98101": 0.1025}},
    "WV": {"default": 0.0647},
    "WI": {"default": 0.0546, "zips": {"53201": 0.0550}},
    "WY": {"default": 0.0536},
    "DC": {"default": 0.0600},
}


def get_labor_rate(state: str, zip_code: str = "") -> float | None:
    """Get prevailing labor rate for state/ZIP. Returns None if not found."""
    state_data = LABOR_RATES.get(state.upper())
    if not state_data:
        return None
    if zip_code and zip_code in state_data.get("zips", {}):
        return state_data["zips"][zip_code]
    return state_data.get("default")


def get_tax_rate(state: str, zip_code: str = "") -> float | None:
    """Get tax rate for state/ZIP. Returns None if not found."""
    state_data = TAX_RATES.get(state.upper())
    if not state_data:
        return None
    if zip_code and zip_code in state_data.get("zips", {}):
        return state_data["zips"][zip_code]
    return state_data.get("default")


def check_labor_rate(estimate_rate: float, state: str, zip_code: str = "") -> dict[str, Any]:
    """Check if estimate labor rate is within 15% of prevailing rate.
    
    Returns dict with: within_range, prevailing, estimate, pct_diff
    """
    prevailing = get_labor_rate(state, zip_code)
    if prevailing is None:
        return {"within_range": None, "prevailing": None, "estimate": estimate_rate, "reason": "No reference data"}
    
    # Allow 15% above, 0% below (can't be lower than prevailing)
    upper_limit = prevailing * 1.15
    pct_diff = ((estimate_rate - prevailing) / prevailing) * 100
    
    return {
        "within_range": estimate_rate <= upper_limit,
        "prevailing": prevailing,
        "estimate": estimate_rate,
        "pct_diff": round(pct_diff, 1),
        "upper_limit": round(upper_limit, 2),
    }


def check_tax_rate(estimate_rate: float, state: str, zip_code: str = "") -> dict[str, Any]:
    """Check if estimate tax rate matches the correct rate.
    
    Returns dict with: matches, expected, actual, tolerance
    """
    expected = get_tax_rate(state, zip_code)
    if expected is None:
        return {"matches": None, "expected": None, "actual": estimate_rate, "reason": "No reference data"}
    
    tolerance = 0.005  # 0.5% tolerance
    return {
        "matches": abs(estimate_rate - expected) <= tolerance,
        "expected": expected,
        "actual": estimate_rate,
        "tolerance": tolerance,
    }
