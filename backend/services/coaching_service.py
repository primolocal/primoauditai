from typing import Dict, List, Any
from collections import Counter
from database.database import SessionLocal
from database.models import FindingReview, AuditRun, ClaimRecord

class CoachingService:
    @staticmethod
    def get_auditors() -> List[str]:
        with SessionLocal() as db:
            result = db.query(FindingReview.auditor_id).filter(FindingReview.auditor_id.isnot(None)).distinct().all()
            return [r[0] for r in result]

    @staticmethod
    def synthesize_auditor_coaching(auditor_id: str) -> Dict[str, Any]:
        """Calculates coaching telemetry and yields qualitative abstraction labels."""
        with SessionLocal() as db:
            # 1. Fetch raw data
            all_reviews = db.query(FindingReview).all()
            all_runs = db.query(AuditRun).all()
            all_claims = db.query(ClaimRecord).all()

            claim_carrier_map = {c.claim_number: c.carrier for c in all_claims}
            audit_claim_map = {run.audit_id: run.claim_id for run in all_runs}
            
            # 2. Build global state mappings
            global_actions_carrier = {} # carrier -> {"confirm": 0, "dismiss": 0, "edit": 0, "total": 0}
            global_actions_overall = {"confirm": 0, "dismiss": 0, "edit": 0, "total": 0}
            
            auditor_actions_carrier = {} 
            auditor_actions_overall = {"confirm": 0, "dismiss": 0, "edit": 0, "total": 0}

            triage_globals = {} # bucket -> {"confirm", "dismiss", "total"}
            triage_auditor = {}

            for rev in all_reviews:
                claim_id = audit_claim_map.get(rev.audit_id)
                carrier = claim_carrier_map.get(claim_id, "Unknown")
                
                outcome = (rev.auditor_outcome or "open").lower()
                if outcome not in ["confirm", "dismiss", "edit"]:
                    continue

                bucket = rev.triage_bucket or "Standard"

                # Global counts
                global_actions_overall["total"] += 1
                global_actions_overall[outcome] += 1
                
                if carrier not in global_actions_carrier:
                    global_actions_carrier[carrier] = {"confirm": 0, "dismiss": 0, "edit": 0, "total": 0}
                global_actions_carrier[carrier]["total"] += 1
                global_actions_carrier[carrier][outcome] += 1

                if bucket not in triage_globals:
                    triage_globals[bucket] = {"confirm": 0, "dismiss": 0, "edit": 0, "total": 0}
                triage_globals[bucket]["total"] += 1
                triage_globals[bucket][outcome] += 1

                # Auditor counts
                if rev.auditor_id == auditor_id:
                    auditor_actions_overall["total"] += 1
                    auditor_actions_overall[outcome] += 1
                    
                    if carrier not in auditor_actions_carrier:
                        auditor_actions_carrier[carrier] = {"confirm": 0, "dismiss": 0, "edit": 0, "total": 0}
                    auditor_actions_carrier[carrier]["total"] += 1
                    auditor_actions_carrier[carrier][outcome] += 1

                    if bucket not in triage_auditor:
                        triage_auditor[bucket] = {"confirm": 0, "dismiss": 0, "edit": 0, "total": 0}
                    triage_auditor[bucket]["total"] += 1
                    triage_auditor[bucket][outcome] += 1

            # 3. Pattern Recognition (Non-punitive translation logic)
            strengths = []
            coaching_opportunities = []
            carrier_breakdown = []

            # Minimum threshold
            min_n = 10
            deviation_threshold = 0.25

            global_confirm_rt = global_actions_overall["confirm"] / max(1, global_actions_overall["total"])
            global_dismiss_rt = global_actions_overall["dismiss"] / max(1, global_actions_overall["total"])

            auditor_confirm_rt = auditor_actions_overall["confirm"] / max(1, auditor_actions_overall["total"])
            auditor_dismiss_rt = auditor_actions_overall["dismiss"] / max(1, auditor_actions_overall["total"])

            # Rule 1: High Overall Alignment
            if auditor_actions_overall["total"] >= min_n:
                if (auditor_confirm_rt - global_confirm_rt) > deviation_threshold:
                    coaching_opportunities.append("Rubber-stamping Pattern: Auditor confirms AI logic substantially more frequently than peers. Coaching required for critical evaluation.")
                elif abs(auditor_confirm_rt - global_confirm_rt) < 0.10 and auditor_confirm_rt > 0.60:
                    strengths.append("High overall alignment and trust in systemic guidelines.")

                if (auditor_dismiss_rt - global_dismiss_rt) > deviation_threshold:
                    coaching_opportunities.append("High Overturn Friction: Auditor broadly dismisses findings at elevated rates compared to peers.")

            # Rule 2: Carrier specifics
            for carr, data in auditor_actions_carrier.items():
                if data["total"] >= 5: # lowered threshold per carrier for testing visibility
                    g_carr = global_actions_carrier.get(carr, {})
                    g_c_dismiss_rt = g_carr.get("dismiss", 0) / max(1, g_carr.get("total", 1))
                    a_c_dismiss_rt = data["dismiss"] / max(1, data["total"])

                    diff = a_c_dismiss_rt - g_c_dismiss_rt
                    
                    diff_flag = "Normal"
                    if diff > 0.35:
                        diff_flag = "Extreme Difficulty"
                        coaching_opportunities.append(f"Specifically struggles with {carr}. Dismisses guidelines {diff*100:.0f}% more frequently than organizational baseline.")
                    elif diff > 0.20:
                        diff_flag = "Elevated Friction"
                    elif diff < -0.20:
                        diff_flag = "High Adherence"
                        strengths.append(f"Highly proficient and compliant with {carr} rules.")
                    
                    carrier_breakdown.append({
                        "carrier": carr,
                        "difficulty_flag": diff_flag
                    })

            # Rule 3: Triage Priorities
            low_ug_data = triage_auditor.get("Low Urgency", {})
            if low_ug_data.get("total", 0) >= 4:
                a_lg_conf = low_ug_data.get("confirm", 0) / low_ug_data["total"]
                if a_lg_conf > 0.8:
                    coaching_opportunities.append("Over-works Low Urgency queues. Approves items that normally auto-resolve or don't require high-touch human validation.")

            ad_fr_data = triage_auditor.get("Address First", {})
            if ad_fr_data.get("total", 0) >= 4:
                a_ad_ovt = ad_fr_data.get("dismiss", 0) / ad_fr_data["total"]
                if a_ad_ovt > 0.5:
                    coaching_opportunities.append("High friction on 'Address First' files. This auditor frequently clashes with prioritized deep-audit files.")
                elif a_ad_ovt < 0.2:
                    strengths.append("Accurately prioritizes and quickly aligns with critical 'Address First' triage scopes.")

            if not strengths and auditor_actions_overall["total"] < min_n:
                strengths.append("Insufficient volume to generate robust strengths modeling yet.")
            
            if not coaching_opportunities and auditor_actions_overall["total"] < min_n:
                coaching_opportunities.append("Continue standard operations while profile builds.")

            return {
                "auditor_id": auditor_id,
                "strengths": strengths,
                "coaching_opportunities": coaching_opportunities,
                "carrier_breakdown": carrier_breakdown,
                "trend_data": [], # Placeholder for historical graphing
                "sample_size": auditor_actions_overall["total"]
            }

    @staticmethod
    def get_contextual_prompts(auditor_id: str, finding_context: Dict[str, Any], carrier: str) -> List[str]:
        """
        Generates situational, non-punitive auditor-facing alerts
        dynamically anchored strictly to specific empirically modeled friction areas.
        """
        if not auditor_id:
            return []
            
        profile = CoachingService.synthesize_auditor_coaching(auditor_id)
        if not profile or profile["sample_size"] < 10:
            return [] # Minimum volume required to show prompts

        prompts = []
        
        # 1. Carrier Guidance
        for carr_diff in profile.get("carrier_breakdown", []):
            if carr_diff["carrier"].lower() == carrier.lower():
                if carr_diff["difficulty_flag"] == "Extreme Difficulty":
                    prompts.append("Internal data shows this carrier frequently requires stronger documentary clarity. Review guidelines closely before overriding.")
                elif carr_diff["difficulty_flag"] == "Elevated Friction":
                    prompts.append("This carrier's logic often drives elevated friction. Please ensure all evidence supports manual alterations.")

        # 2. Category/Playbook/General Caution Guidance based on Opportunities
        opportunities = profile.get("coaching_opportunities", [])
        
        # Rubber stamping
        if any("Rubber-stamping" in opp for opp in opportunities):
            # General prompt randomly injected to ensure we don't spam it on EVERY finding if it's general
            if finding_context.get("severity") in ["critical", "high"]:
                 prompts.append("High severity guidelines require manual validation. Verify operational nuances instead of auto-confirming.")
                 
        # Over-dismissals / "High Overturn Friction"
        if any("High Overturn Friction" in opp for opp in opportunities):
            prompts.append("This automated finding type is empirically difficult to contest safely. Verify documentation heavily before dismissing.")
            
        # Triage Priority Overrides
        bucket = finding_context.get("triage_bucket", "Standard")
        if bucket == "Address First":
             if any("High friction on 'Address First'" in opp for opp in opportunities):
                 prompts.append("Priority 'Address First' files typically hold deep structural validity. Thorough appraisal required to safely dismiss.")
                 
        if bucket == "Low Urgency":
             if any("Over-works Low Urgency" in opp for opp in opportunities):
                 prompts.append("Low Urgency items often self-resolve or do not warrant heavy manual validation touches.")

        return prompts
