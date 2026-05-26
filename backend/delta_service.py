from typing import Dict, Any

class DeltaService:
    @staticmethod
    def annotate(parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Scans parsed EMS panels and rows.
        1. Identifies active supplement (highest LINE_IND/supplement string).
        2. Injects `delta_status` ('added', 'unchanged', 'original') into each row.
        """
        claim = parsed_data.get("claim", {})
        panels = claim.get("panels", [])
        
        # 1. Determine active supplement
        all_supps = set()
        for p in panels:
            for r in p.get("rows", []):
                s = r.get("supplement", "").upper().strip()
                if s: all_supps.add(s)
                
        # Logic: E01, then S01, S02, etc. (alphanumeric sort usually works for standard CCC EMS)
        active_supp = "E01"
        if all_supps:
            active_supp = sorted(list(all_supps))[-1]
            
        # 2. Annotate lines
        for p in panels:
            for r in p.get("rows", []):
                s = r.get("supplement", "").upper().strip()
                
                # If no supplement explicitly tagged, or tagged as E01
                if not s or s == "E01":
                     if active_supp == "E01" or not s:
                         r["delta_status"] = "original"
                     else:
                         r["delta_status"] = "unchanged" # Historical original line
                else:
                     if s == active_supp:
                         r["delta_status"] = "added"
                     else:
                         r["delta_status"] = "unchanged" # Prior supplement line
                         
        parsed_data["active_supplement"] = active_supp
        return parsed_data
