"""
Dent Wizard Hail Pricing Matrix — NGIC (National General Insurance Company)
Maps panel type + dent count + coin size → allowed PDR price.
"""
import re
from typing import Optional, Tuple

# Dent count brackets → severity class
DENT_BRACKETS = {
    (1, 5): "VERY LIGHT",
    (6, 15): "LIGHT",
    (16, 30): "MODERATE",
    (31, 50): "MEDIUM",
    (51, 75): "HEAVY",
}

# Coin sizes
COIN_SIZES = ["DIME", "NICKEL", "QUARTER", "HALF"]

# Matrix: (panel, severity, coin_size) → price
# "MCE" = Most Cost Effective (consult Dent Wizard)
# None = not listed
MATRIX = {
    # HOOD
    ("HOOD", "VERY LIGHT", "DIME"): 75, ("HOOD", "VERY LIGHT", "NICKEL"): 100,
    ("HOOD", "VERY LIGHT", "QUARTER"): 125, ("HOOD", "VERY LIGHT", "HALF"): 150,
    ("HOOD", "LIGHT", "DIME"): 125, ("HOOD", "LIGHT", "NICKEL"): 175,
    ("HOOD", "LIGHT", "QUARTER"): 200, ("HOOD", "LIGHT", "HALF"): 300,
    ("HOOD", "MODERATE", "DIME"): 200, ("HOOD", "MODERATE", "NICKEL"): 250,
    ("HOOD", "MODERATE", "QUARTER"): 300, ("HOOD", "MODERATE", "HALF"): 400,
    ("HOOD", "MEDIUM", "DIME"): 300, ("HOOD", "MEDIUM", "NICKEL"): 350,
    ("HOOD", "MEDIUM", "QUARTER"): 425, ("HOOD", "MEDIUM", "HALF"): 525,
    ("HOOD", "HEAVY", "DIME"): 400, ("HOOD", "HEAVY", "NICKEL"): 475,
    ("HOOD", "HEAVY", "QUARTER"): 550, ("HOOD", "HEAVY", "HALF"): 650,
    # ROOF
    ("ROOF", "VERY LIGHT", "DIME"): 100, ("ROOF", "VERY LIGHT", "NICKEL"): 125,
    ("ROOF", "VERY LIGHT", "QUARTER"): 150, ("ROOF", "VERY LIGHT", "HALF"): 200,
    ("ROOF", "LIGHT", "DIME"): 175, ("ROOF", "LIGHT", "NICKEL"): 225,
    ("ROOF", "LIGHT", "QUARTER"): 250, ("ROOF", "LIGHT", "HALF"): 400,
    ("ROOF", "MODERATE", "DIME"): 250, ("ROOF", "MODERATE", "NICKEL"): 300,
    ("ROOF", "MODERATE", "QUARTER"): 375, ("ROOF", "MODERATE", "HALF"): 525,
    ("ROOF", "MEDIUM", "DIME"): 375, ("ROOF", "MEDIUM", "NICKEL"): 450,
    ("ROOF", "MEDIUM", "QUARTER"): 550, ("ROOF", "MEDIUM", "HALF"): 675,
    ("ROOF", "HEAVY", "DIME"): 475, ("ROOF", "HEAVY", "NICKEL"): 575,
    ("ROOF", "HEAVY", "QUARTER"): 700, ("ROOF", "HEAVY", "HALF"): 825,
    # DECK LID
    ("DECK LID", "VERY LIGHT", "DIME"): 75, ("DECK LID", "VERY LIGHT", "NICKEL"): 100,
    ("DECK LID", "VERY LIGHT", "QUARTER"): 125, ("DECK LID", "VERY LIGHT", "HALF"): 150,
    ("DECK LID", "LIGHT", "DIME"): 125, ("DECK LID", "LIGHT", "NICKEL"): 175,
    ("DECK LID", "LIGHT", "QUARTER"): 200, ("DECK LID", "LIGHT", "HALF"): 300,
    ("DECK LID", "MODERATE", "DIME"): 200, ("DECK LID", "MODERATE", "NICKEL"): 250,
    ("DECK LID", "MODERATE", "QUARTER"): 300, ("DECK LID", "MODERATE", "HALF"): 400,
    ("DECK LID", "MEDIUM", "DIME"): 300, ("DECK LID", "MEDIUM", "NICKEL"): 350,
    ("DECK LID", "MEDIUM", "QUARTER"): 425, ("DECK LID", "MEDIUM", "HALF"): 525,
    ("DECK LID", "HEAVY", "DIME"): 400, ("DECK LID", "HEAVY", "NICKEL"): 475,
    ("DECK LID", "HEAVY", "QUARTER"): 550, ("DECK LID", "HEAVY", "HALF"): 650,
    # QUARTER
    ("QUARTER", "VERY LIGHT", "DIME"): 75, ("QUARTER", "VERY LIGHT", "NICKEL"): 100,
    ("QUARTER", "VERY LIGHT", "QUARTER"): 125, ("QUARTER", "VERY LIGHT", "HALF"): 150,
    ("QUARTER", "LIGHT", "DIME"): 125, ("QUARTER", "LIGHT", "NICKEL"): 150,
    ("QUARTER", "LIGHT", "QUARTER"): 175, ("QUARTER", "LIGHT", "HALF"): 225,
    ("QUARTER", "MODERATE", "DIME"): 200, ("QUARTER", "MODERATE", "NICKEL"): 225,
    ("QUARTER", "MODERATE", "QUARTER"): 250,
    ("QUARTER", "MEDIUM", "DIME"): 300, ("QUARTER", "MEDIUM", "NICKEL"): 325,
    ("QUARTER", "MEDIUM", "QUARTER"): 400,
    # ROOF RAIL
    ("ROOF RAIL", "VERY LIGHT", "DIME"): 100, ("ROOF RAIL", "VERY LIGHT", "NICKEL"): 125,
    ("ROOF RAIL", "VERY LIGHT", "QUARTER"): 150, ("ROOF RAIL", "VERY LIGHT", "HALF"): 200,
    ("ROOF RAIL", "LIGHT", "DIME"): 150, ("ROOF RAIL", "LIGHT", "NICKEL"): 200,
    ("ROOF RAIL", "LIGHT", "QUARTER"): 250,
    ("ROOF RAIL", "MODERATE", "DIME"): 250, ("ROOF RAIL", "MODERATE", "NICKEL"): 300,
    ("ROOF RAIL", "MODERATE", "QUARTER"): 450,
    ("ROOF RAIL", "MEDIUM", "DIME"): 450, ("ROOF RAIL", "MEDIUM", "NICKEL"): 550,
    # DOOR
    ("DOOR", "VERY LIGHT", "DIME"): 75, ("DOOR", "VERY LIGHT", "NICKEL"): 100,
    ("DOOR", "VERY LIGHT", "QUARTER"): 125, ("DOOR", "VERY LIGHT", "HALF"): 150,
    ("DOOR", "LIGHT", "DIME"): 125, ("DOOR", "LIGHT", "NICKEL"): 150,
    ("DOOR", "LIGHT", "QUARTER"): 175, ("DOOR", "LIGHT", "HALF"): 225,
    ("DOOR", "MODERATE", "DIME"): 200, ("DOOR", "MODERATE", "NICKEL"): 225,
    ("DOOR", "MODERATE", "QUARTER"): 250,
    ("DOOR", "MEDIUM", "DIME"): 300, ("DOOR", "MEDIUM", "NICKEL"): 325,
    # UPPER DOOR FRAME
    ("UPPER DOOR FRAME", "VERY LIGHT", "DIME"): 100, ("UPPER DOOR FRAME", "VERY LIGHT", "NICKEL"): 125,
    ("UPPER DOOR FRAME", "VERY LIGHT", "QUARTER"): 150, ("UPPER DOOR FRAME", "VERY LIGHT", "HALF"): 200,
    ("UPPER DOOR FRAME", "LIGHT", "DIME"): 150, ("UPPER DOOR FRAME", "LIGHT", "NICKEL"): 200,
    # FENDER
    ("FENDER", "VERY LIGHT", "DIME"): 75, ("FENDER", "VERY LIGHT", "NICKEL"): 100,
    ("FENDER", "VERY LIGHT", "QUARTER"): 125, ("FENDER", "VERY LIGHT", "HALF"): 150,
    ("FENDER", "LIGHT", "DIME"): 125, ("FENDER", "LIGHT", "NICKEL"): 150,
    ("FENDER", "LIGHT", "QUARTER"): 175, ("FENDER", "LIGHT", "HALF"): 225,
    ("FENDER", "MODERATE", "DIME"): 200, ("FENDER", "MODERATE", "NICKEL"): 225,
    ("FENDER", "MODERATE", "QUARTER"): 250,
    ("FENDER", "MEDIUM", "DIME"): 300, ("FENDER", "MEDIUM", "NICKEL"): 325,
    # LIFT GATE
    ("LIFT GATE", "VERY LIGHT", "DIME"): 75, ("LIFT GATE", "VERY LIGHT", "NICKEL"): 100,
    ("LIFT GATE", "VERY LIGHT", "QUARTER"): 125, ("LIFT GATE", "VERY LIGHT", "HALF"): 150,
    ("LIFT GATE", "LIGHT", "DIME"): 125, ("LIFT GATE", "LIGHT", "NICKEL"): 175,
    ("LIFT GATE", "LIGHT", "QUARTER"): 200, ("LIFT GATE", "LIGHT", "HALF"): 300,
    ("LIFT GATE", "MODERATE", "DIME"): 200, ("LIFT GATE", "MODERATE", "NICKEL"): 250,
    ("LIFT GATE", "MODERATE", "QUARTER"): 300,
    ("LIFT GATE", "MEDIUM", "DIME"): 300, ("LIFT GATE", "MEDIUM", "NICKEL"): 350,
    ("LIFT GATE", "MEDIUM", "QUARTER"): 425,
}

# Panel name aliases (from estimate descriptions → matrix panel keys)
PANEL_ALIASES = {
    "hood": "HOOD",
    "roof": "ROOF",
    "deck lid": "DECK LID", "trunk": "DECK LID",
    "quarter": "QUARTER", "quarter panel": "QUARTER",
    "roof rail": "ROOF RAIL",
    "door": "DOOR", "door shell": "DOOR",
    "upper door frame": "UPPER DOOR FRAME",
    "fender": "FENDER",
    "lift gate": "LIFT GATE", "tail gate": "LIFT GATE", "liftgate": "LIFT GATE",
    "cowl": "COWL",
}


def lookup_price(panel: str, dent_count: int, coin_size: str) -> Optional[int]:
    """Look up the matrix price for a given panel, dent count, and coin size."""
    panel_key = PANEL_ALIASES.get(panel.lower())
    if not panel_key:
        return None

    # Find severity class
    severity = None
    for (lo, hi), sev in DENT_BRACKETS.items():
        if lo <= dent_count <= hi:
            severity = sev
            break

    if not severity:
        return None

    coin_key = coin_size.upper()
    if coin_key == "NKL":
        coin_key = "NICKEL"
    if coin_key == "QTR":
        coin_key = "QUARTER"

    return MATRIX.get((panel_key, severity, coin_key))


def check_pdr_price(panel: str, dent_count: int, coin_size: str, actual_price: float) -> dict:
    """
    Check if a PDR price matches the Dent Wizard matrix.
    Returns: {"match": bool, "expected": int|None, "actual": float, "note": str}
    """
    expected = lookup_price(panel, dent_count, coin_size)
    if expected is None:
        return {"match": None, "expected": None, "actual": actual_price,
                "note": f"Panel '{panel}' not found in matrix or exceeds limits"}

    if expected == "MCE":
        return {"match": None, "expected": "MCE", "actual": actual_price,
                "note": "MCE — consult Dent Wizard. Price cannot be auto-verified."}

    if isinstance(expected, (int, float)):
        if actual_price == expected:
            return {"match": True, "expected": expected, "actual": actual_price, "note": "Exact match"}
        elif abs(actual_price - expected) <= expected * 0.15:
            return {"match": True, "expected": expected, "actual": actual_price,
                    "note": f"Within 15% of matrix (${expected})"}
        else:
            return {"match": False, "expected": expected, "actual": actual_price,
                    "note": f"Price ${actual_price:.0f} vs matrix ${expected:.0f} — verify"}
