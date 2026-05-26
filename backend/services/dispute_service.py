from typing import Dict, Any, List

class DisputeSimulationService:
    @staticmethod
    def calculate_dispute_risk(finding: Dict[str, Any], carrier: str) -> Dict[str, Any]:
        """
        Calculates a predictive 'dispute_risk_score' based on various finding vectors.
        Maps the score to a category and assigns targeted recommendations.
        """
        score = 0
        reasons = []
        
        # 1. Base rule type risk
        rule_id = finding.get("rule_id", "").lower()
        if "labor" in rule_id:
            score += 35
            reasons.append("Labor rules are historically heavily disputed by carrier estimators.")
        elif "parts" in rule_id or "oem" in rule_id:
            score += 25
            reasons.append("Parts selection changes carry moderate-to-high disagreement risk.")
        elif "photo" in rule_id or "visual" in rule_id:
            score += 15
        
        # 2. Carrier friction multiplier
        high_friction_carriers = ["National General", "NatGen", "Elephant", "Penn National"]
        if any(c.lower() in carrier.lower() for c in high_friction_carriers):
            score += 20
            reasons.append(f"Carrier '{carrier}' operates with high procedural friction and strict thresholds.")
            
        # 3. Evidence strength penalty
        ev_refs = finding.get("evidence_refs", [])
        if not any(e.get("support_status") == "verified" for e in ev_refs):
            if any(e.get("support_status") == "missing" for e in ev_refs):
                score += 30
                reasons.append("Missing verified evidence drastically increases probability of a dispute.")
                
        # 4. Phase 15 Historical Overturn rate overlaps
        signals = finding.get("historical_signals", [])
        if any("overturn" in sig.get("type", "").lower() for sig in signals):
            score += 25
            reasons.append("Historical telemetry indicates frequent overturns for this exact finding pattern.")
            
        # 5. Vision result penalty
        if finding.get("vision_result") and finding["vision_result"].get("confidence", 1.0) < 0.6:
            score += 15
            reasons.append("Sub-optimal computer vision confidence leaves visual evidence open to interpretation.")
            
        # Clamp score
        score = min(score, 100)
        
        # If no explicit danger reasons popped up, emit a baseline reason
        if not reasons:
            reasons = [
                "LOW RISK (Routine Pattern)",
                "• No abnormal dispute signals detected",
                "• Standard documentation rules still apply"
            ]
            
        # Category Mapping
        category = "Low"
        rec_action = "proceed"
        
        if score > 75:
            category = "Very High"
            rec_action = "request support / escalate"
        elif score > 50:
            category = "High"
            rec_action = "follow playbook"
        elif score > 25:
            category = "Moderate"
            rec_action = "review evidence"

        return {
            "score": score,
            "category": category,
            "reasons": reasons[:3], # At most 3 concise reasons
            "recommended_action": rec_action
        }
