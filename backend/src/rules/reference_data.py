"""
Reference data for QC verification — labor rates and tax rates by ZIP/state.
Data sources: State labor rate surveys, tax authority tables.

To update: edit the LABOR_RATES and TAX_RATES dicts below.
"""

from typing import Any

# ── Labor Rates (per hour, by state and optionally by ZIP) ──
# Structure: {"TX": {"default": 62.00, "zips": {"76009": 68.00, "75001": 65.00}}}
# Default rate if ZIP not found in state
LABOR_RATES: dict[str, dict[str, Any]] = {
    "TX": {
        "default": 62.00,
        "zips": {
            "76009": 68.00,   # Alvarado
            "76028": 65.00,   # Burleson
            "75001": 66.00,   # Addison
            "75201": 70.00,   # Dallas
            "77001": 72.00,   # Houston
            "78701": 68.00,   # Austin
            "78201": 65.00,   # San Antonio
        },
    },
    "IL": {
        "default": 70.00,
        "zips": {
            "60015": 72.00,   # Deerfield
            "60601": 75.00,   # Chicago
        },
    },
    "MT": {
        "default": 65.00,
        "zips": {
            "59714": 65.00,   # Belgrade
            "59715": 65.00,
        },
    },
    "MO": {
        "default": 58.00,
        "zips": {
            "64772": 55.00,   # Nevada
        },
    },
    "NJ": {
        "default": 75.00,
    },
    "AZ": {
        "default": 68.00,
        "zips": {
            "85001": 70.00,   # Phoenix
        },
    },
}

# ── Tax Rates (sales tax, by state and ZIP) ──
# Structure: {"TX": {"default": 0.0625, "zips": {"76009": 0.0825}}}
TAX_RATES: dict[str, dict[str, Any]] = {
    "TX": {
        "default": 0.0625,
        "zips": {
            "76009": 0.0825,  # Alvarado — 8.25%
            "76028": 0.0825,  # Burleson
            "75001": 0.0825,
        },
    },
    "IL": {
        "default": 0.0625,
        "zips": {
            "60015": 0.0700,  # Deerfield
            "60601": 0.1025,  # Chicago
        },
    },
    "MT": {
        "default": 0.0000,   # Montana — no sales tax
    },
    "MO": {
        "default": 0.04225,
        "zips": {
            "64772": 0.05725,  # Nevada
        },
    },
    "NJ": {
        "default": 0.06625,
    },
    "AZ": {
        "default": 0.0560,
        "zips": {
            "85001": 0.0860,  # Phoenix
        },
    },
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
