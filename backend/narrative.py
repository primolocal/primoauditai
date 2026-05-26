from typing import List, Dict, Any

class NarrativeService:
    @staticmethod
    def generate(findings: List[Dict[str, Any]], score_data: Dict[str, Any], active_supplement: str = "E01") -> Dict[str, Any]:
        """Generates the narrative summary based on active findings and final score."""
        
        # Determine actionable vs overridden
        active_findings = [f for f in findings if f.get("status") != "overridden"]
        overrides = [f for f in findings if f.get("status") == "overridden"]
        
        # Supplement scoping
        supp_findings = [f for f in active_findings if f.get("is_supplement_issue", False)]
        
        verdict = score_data.get("verdict", "Pass")
        score = score_data.get("score", 100)
        
        damage_summary = f"Estimate review generated a score of {score}/100."
        if active_supplement != "E01":
            damage_summary += f" Evaluated against {active_supplement} scope delta."
            
        if verdict == "Review Required":
            damage_summary += " Significant carrier compliance issues detected."
            
        claim_summary = ""
        if len(active_findings) == 0:
            claim_summary = "No actionable findings. Ready for approval."
        else:
            if active_supplement != "E01":
                claim_summary = f"Identified {len(supp_findings)} active issues specifically authored in {active_supplement}."
            else:
                claim_summary = f"Identified {len(active_findings)} active issues requiring auditor attention."
            
        reviewer_notes = ""
        if len(overrides) > 0:
             reviewer_notes = f"Auditor has manually overridden {len(overrides)} system flags."
             
        escalation_note = "Escalate to manager if structural damage severity is ambiguous." if score < 70 else ""
        
        return {
            "damage_summary": damage_summary,
            "claim_summary": claim_summary,
            "reviewer_notes": reviewer_notes,
            "escalation_note": escalation_note
        }
