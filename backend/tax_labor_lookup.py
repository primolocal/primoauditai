"""
Tax & Labor Rate Lookup — JSON-based with all rate types.
"""
import json, os

_DATA = None
def _load():
    global _DATA
    if _DATA: return _DATA
    path = os.path.join(os.path.dirname(__file__), "data", "rates.json")
    if not os.path.exists(path):
        _DATA = {"labor": {}, "taxes": {}}
        return _DATA
    with open(path) as f:
        _DATA = json.load(f)
    return _DATA

def lookup_labor(zip_code: str) -> dict:
    data = _load()
    return data["labor"].get(str(zip_code).zfill(5)[:5], {})

def lookup_tax(zip_code: str) -> dict:
    data = _load()
    return data["taxes"].get(str(zip_code).zfill(5)[:5], {})
