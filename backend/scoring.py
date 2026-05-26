from typing import List, Dict, Any

class ScoringService:
    @staticmethod
    def calculate(findings: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculates scorecard and summary counts given a list of unified finding dictionaries."""
        base_point_deductions = 0
        natgen_point_deductions = 0
        severity_points = {"high": 10, "medium": 5, "low": 2, "critical": 10, "major": 5, "minor": 2}

        base_cat_deductions = {
            "structural_integrity": 0, "line_item_support": 0, "parts_accuracy": 0,
            "labor_reasonableness": 0, "documentation_readiness": 0, "carrier_compliance": 0
        }
        natgen_cat_deductions = {
            "structural_integrity": 0, "line_item_support": 0, "parts_accuracy": 0,
            "labor_reasonableness": 0, "documentation_readiness": 0, "carrier_compliance": 0
        }

        finding_counts = {"high": 0, "medium": 0, "low": 0}

        for f in findings:
            if f.get("status") == "overridden":
                # Overridden findings don't count against the score
                continue

            sev = f.get("severity", "low")
            if sev in ["critical", "high"]: sev_key = "high"
            elif sev in ["major", "medium"]: sev_key = "medium"
            else: sev_key = "low"
            
            finding_counts[sev_key] += 1
            pts = severity_points.get(sev, 0)
            cat = f.get("category", "carrier_compliance")
            
            if f.get("rule_id", "").startswith("NATGEN"):
                natgen_point_deductions += pts
                if cat in natgen_cat_deductions:
                    natgen_cat_deductions[cat] += pts
            else:
                base_point_deductions += pts
                if cat in base_cat_deductions:
                    base_cat_deductions[cat] += pts

        def get_verdict(score):
            if score >= 85: return "Clean", "low"
            if score >= 70: return "Minor Review", "moderate"
            if score >= 55: return "Review Required", "elevated"
            return "High Risk", "high"
            
        base_cat_scores = { k: max(0, 100 - v) for k, v in base_cat_deductions.items() }
        adj_cat_scores = { k: max(0, 100 - (base_cat_deductions[k] + natgen_cat_deductions[k])) for k in base_cat_deductions.keys() }

        base_final = max(0, 100 - base_point_deductions)
        adj_final = max(0, 100 - (base_point_deductions + natgen_point_deductions))
        base_verdict, base_risk_level = get_verdict(base_final)
        adj_verdict, adj_risk_level = get_verdict(adj_final)

        return {
            "base_score": base_final,
            "base_verdict": base_verdict,
            "base_risk_level": base_risk_level,
            "carrier_adjusted_score": adj_final,
            "carrier_adjusted_verdict": adj_verdict,
            "carrier_adjusted_risk_level": adj_risk_level,
            "score": adj_final,
            "risk_level": adj_risk_level,
            "verdict": adj_verdict,
            "category_scores": adj_cat_scores,
            "base_category_scores": base_cat_scores,
            "finding_counts": finding_counts,
        }
