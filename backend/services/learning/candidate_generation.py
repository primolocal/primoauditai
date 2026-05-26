"""
Learning — Candidate generation and lifecycle management.
Extracted from services/learning_service.py
"""
import hashlib
import json
from datetime import datetime
from typing import Dict, List, Any
from collections import Counter

from database.database import SessionLocal
from database.models import LearningCandidate
from schemas import LearningCandidateType, TruthStatusEnum

# High-Friction Carrier Multiplier Map
CARRIER_FRICTION_MAP = {
    "National General": 1.5,
    "NatGen": 1.5,
    "Elephant": 1.5,
    "Penn National": 1.5
}


def generate_learning_candidates(min_n: int = 10) -> Dict[str, Any]:
    """Scans truth/logic matrices and generates structured LearningCandidate improvement opportunities safely."""
    from services.learning.metrics import synthesize_metrics, synthesize_hermes_effectiveness

    report = synthesize_metrics(test_mode=False)
    insights = report.get("insights", [])
    rule_metrics = report.get("rule_metrics", [])

    hermes = synthesize_hermes_effectiveness()
    h_perf = hermes.get("performance_metrics", [])
    triage_metrics = hermes.get("triage_metrics", {})
    playbook_metrics = hermes.get("playbook_metrics", {})

    candidates_created = []

    with SessionLocal() as db:
        def is_duplicate(fp: str) -> bool:
            return db.query(LearningCandidate).filter_by(candidate_fingerprint=fp).first() is not None

        def add_cand(ctype, rule_id, desc, evidence, conf, source, sample_sz, freq, impact, extra_fp="", carrier=None):
            fp = hashlib.sha256(f"{ctype}::{rule_id}::{source}::{extra_fp}".encode('utf-8')).hexdigest()

            freq_mult = min(freq / 20.0, 2.0) if freq > 0 else 0.5
            priority = round(impact * conf * freq_mult, 2)

            if not is_duplicate(fp):
                cand = LearningCandidate(
                    candidate_fingerprint=fp,
                    type=LearningCandidateType(ctype) if hasattr(LearningCandidateType, ctype) else ctype,
                    rule_id=rule_id,
                    description=desc,
                    evidence_json=evidence,
                    confidence_score=round(conf, 2),
                    priority_score=priority,
                    source=source,
                    sample_size=sample_sz,
                    affected_carriers=[carrier] if carrier else [],
                    affected_rules=[rule_id] if rule_id and rule_id != "UNKNOWN" else []
                )
                db.add(cand)
                candidates_created.append(ctype)

        # 1. Logic & Action Drift
        for insight in insights:
            m = insight.get("metrics", {})
            rule_id = insight.get("rule_id", "UNKNOWN")
            sample_sz = m.get("finding_decisions", 0) + m.get("rec_decisions", 0)

            if insight.get("type") == "Logic Drift":
                val_count = m.get("truth_finding_validated", 0)
                over_count = m.get("truth_finding_overturned", 0)

                if over_count > val_count:
                    ctype = "RULE_ADJUSTMENT"
                    desc = f"Rule '{rule_id}' has a {insight.get('severity')} rejection rate AND real-world carrier data confirms the logic is frequently overturned. Adjustment required."
                else:
                    ctype = "WORDING_ADJUSTMENT"
                    desc = f"Rule '{rule_id}' has a {insight.get('severity')} rejection rate, YET real-world carrier data validates it. Reviewers may be rejecting due to abrasive or unclear compliance wording."

                impact = 8.0 if insight.get("severity") == "critical" else 5.0
                conf = m.get("finding_reject_rate", 0)
                add_cand(ctype, rule_id, desc, m, conf, "rule", sample_sz, sample_sz, impact)

            elif insight.get("type") == "Action Severity Drift":
                ctype = "RECOMMENDATION_TUNING"
                desc = f"Action mitigations for '{rule_id}' are frequently manually overridden by analysts. Tuning required for payload structure."
                impact = 7.0 if insight.get("severity") == "critical" else 4.0
                conf = m.get("rec_reject_rate", 0)
                add_cand(ctype, rule_id, desc, m, conf, "rule", sample_sz, sample_sz, impact)

        # 2. Rule Metrics Discrepancies
        for m in rule_metrics:
            rule_id = m.get("rule_id", "UNKNOWN")
            sample_sz = m.get("finding_decisions", 0) + m.get("rec_decisions", 0)

            sys_corr_rev_wrong = m.get("truth_sys_correct_rev_wrong", 0)
            if sys_corr_rev_wrong >= min_n:
                ctype = "WORDING_ADJUSTMENT"
                desc = f"Analysts are continually suppressing '{rule_id}' logic, but carrier reality proves the System correct. Consider workflow/training interventions."
                add_cand(ctype, rule_id, desc, m, 0.85, "rule", sample_sz, sys_corr_rev_wrong, 6.0, "sys_corr_rev_wrong")

            both_wrong = m.get("truth_both_wrong_missed", 0)
            if both_wrong >= min_n:
                ctype = "MISSED_PATTERN_ALERT"
                desc = f"A recurring carrier exception loosely associated with '{rule_id}' is consistently missed by both analysts and automated intelligence. New logic expansion required."
                add_cand(ctype, rule_id, desc, m, 0.9, "rule", sample_sz, both_wrong, 8.5, "both_wrong")

            if m.get("carrier_rejections"):
                for carrier, count in m.get("carrier_rejections").items():
                    if count >= min_n:
                        ctype = "CARRIER_SPECIFIC_BEHAVIOR"
                        desc = f"Carrier '{carrier}' overwhelmingly rejects base configurations for '{rule_id}'. Implement isolated carrier sub-rule."
                        ev = {"carrier": carrier, "count": count, "full_metrics": m}
                        add_cand(ctype, rule_id, desc, ev, 0.8, "carrier", count, count, 7.0, carrier, carrier=carrier)

        # 3. Hermes Wording Performance
        for m in h_perf:
            total_gen = m["total_generated"]
            if total_gen < 5: continue

            reject_rate = m["rejected"] / total_gen
            modify_rate = m["modified"] / total_gen

            if modify_rate > 0.4:
                ctype = "WORDING_ADJUSTMENT"
                desc = f"Template {m['template_family']} variant {m['wording_variant']} modified {modify_rate*100:.1f}% of the time despite firm rule logic."
                add_cand(ctype, "HERMES", desc, m, modify_rate, "hermes", total_gen, total_gen, 5.5, f"wording_{m['template_family']}_{m['wording_variant']}")

            elif reject_rate > 0.5 and m["advisory_tone"] in ["firm", "cautionary"]:
                ctype = "RECOMMENDATION_TUNING"
                desc = f"Tone {m['advisory_tone']} too aggressive for carrier {m['carrier']}. Rejected {reject_rate*100:.1f}%."
                add_cand(ctype, "HERMES", desc, m, reject_rate, "hermes", total_gen, total_gen, 6.5, f"tone_{m['carrier']}_{m['advisory_tone']}", carrier=m["carrier"])

            elif m["carrier"] != "overall" and reject_rate > 0.4:
                ctype = "CARRIER_SPECIFIC_BEHAVIOR"
                desc = f"Template {m['template_family']} significantly underperforms selectively against {m['carrier']}."
                add_cand(ctype, "HERMES", desc, m, reject_rate, "hermes", total_gen, total_gen, 6.0, f"spec_{m['template_family']}_{m['carrier']}", carrier=m["carrier"])

        # 4. Triage Anomalies
        low_ug = triage_metrics.get("overall", {}).get("Low Urgency", {})
        if low_ug.get("total", 0) >= 10:
            conf_rt = low_ug.get("confirm", 0) / low_ug["total"]
            if conf_rt >= 0.30:
                add_cand("TRIAGE_TUNING", "TRIAGE", f"Low Urgency queue under-prioritized: {conf_rt*100:.1f}% manual confirmation rate.", low_ug, conf_rt, "triage", low_ug["total"], low_ug["total"], 7.0, "low_ug")

        addr_frst = triage_metrics.get("overall", {}).get("Address First", {})
        if addr_frst.get("total", 0) >= 10:
            ovt_rt = addr_frst.get("overturn", 0) / addr_frst["total"]
            if ovt_rt >= 0.35:
                add_cand("TRIAGE_TUNING", "TRIAGE", f"Address First queue over-prioritized: {ovt_rt*100:.1f}% manual overturn rate.", addr_frst, ovt_rt, "triage", addr_frst["total"], addr_frst["total"], 8.5, "addr_first")

        for c_name, c_data in triage_metrics.get("carriers", {}).items():
            if c_name == "overall": continue
            for b_name, b_val in c_data.items():
                if b_val.get("total", 0) >= 8:
                    c_conf = b_val.get("confirm", 0) / b_val["total"]
                    glob_b = triage_metrics.get("overall", {}).get(b_name, {})
                    glob_conf = glob_b.get("confirm", 0) / max(glob_b.get("total", 1), 1)
                    if abs(c_conf - glob_conf) >= 0.15:
                        add_cand("CARRIER_SPECIFIC_BEHAVIOR", "TRIAGE", f"Carrier {c_name} diverges on {b_name}: {c_conf*100:.1f}% conf vs {glob_conf*100:.1f}% global.", b_val, abs(c_conf - glob_conf), "triage", b_val["total"], b_val["total"], 6.0, f"carr_{c_name}_{b_name}", carrier=c_name)

        # 5. Playbook Anomalies
        for a_name, a_val in playbook_metrics.get("actions", {}).items():
            if a_val.get("total", 0) >= 10:
                ov_rate = a_val.get("overturn", 0) / a_val["total"]
                if ov_rate > 0.35:
                    add_cand("PLAYBOOK_TUNING", "PLAYBOOK", f"Procedural Playbook '{a_name}' faces high overturn rate: {ov_rate*100:.1f}% manual rejection.", a_val, ov_rate, "playbook", a_val["total"], a_val["total"], 8.0, f"pb_{a_name}")

        for c_name, c_acts in playbook_metrics.get("carriers", {}).items():
            if c_name == "overall": continue
            for a_name, a_val in c_acts.items():
                if a_val.get("total", 0) >= 8:
                    c_ov = a_val.get("overturn", 0) / a_val["total"]
                    glob_a = playbook_metrics.get("actions", {}).get(a_name, {})
                    glob_ov = glob_a.get("overturn", 0) / max(glob_a.get("total", 1), 1)
                    if (c_ov - glob_ov) >= 0.15:
                        add_cand("CARRIER_SPECIFIC_BEHAVIOR", "PLAYBOOK", f"Carrier {c_name} disproportionately rejects playbook '{a_name}': {c_ov*100:.1f}% vs {glob_ov*100:.1f}% global.", a_val, abs(c_ov - glob_ov), "playbook", a_val["total"], a_val["total"], 7.5, f"pbcarr_{c_name}_{a_name}", carrier=c_name)

        db.commit()
        return {"generated_count": len(candidates_created), "types": dict(Counter(candidates_created))}


def get_candidates(status_filter: str = "all") -> List[Dict[str, Any]]:
    with SessionLocal() as db:
        query = db.query(LearningCandidate)
        if status_filter and status_filter != "all":
            query = query.filter_by(status=status_filter)
        cands = query.order_by(LearningCandidate.priority_score.desc()).all()

        return [{
            "id": c.id,
            "type": c.type.value if hasattr(c.type, 'value') else str(c.type),
            "rule_id": c.rule_id,
            "description": c.description,
            "evidence_json": c.evidence_json,
            "confidence_score": c.confidence_score,
            "priority_score": c.priority_score,
            "source": c.source,
            "affected_carriers": c.affected_carriers,
            "affected_rules": c.affected_rules,
            "sample_size": c.sample_size,
            "example_evidence_json": c.example_evidence_json,
            "status": c.status,
            "implementation_status": c.implementation_status,
            "git_commit_hash": c.git_commit_hash,
            "change_type": c.change_type,
            "rule_version": c.rule_version,
            "prompt_version": c.prompt_version,
            "deployed_at": c.deployed_at.isoformat() if c.deployed_at else None,
            "implemented_by": c.implemented_by,
            "effectiveness_status": c.effectiveness_status,
            "impact_summary_json": c.impact_summary_json,
            "admin_note": c.admin_note,
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "reviewed_at": c.reviewed_at.isoformat() if c.reviewed_at else None,
            "reviewed_by": c.reviewed_by
        } for c in cands]


def review_candidate(candidate_id: int, status: str, admin_name: str = "system_admin", note: str = None) -> Dict[str, Any]:
    """Strictly updates learning candidate status without mutating base rules. Advisory boundary."""
    with SessionLocal() as db:
        c = db.query(LearningCandidate).filter_by(id=candidate_id).first()
        if not c:
            return {"error": "Candidate not found"}

        c.status = status
        c.reviewed_at = datetime.utcnow()
        c.reviewed_by = admin_name
        if note:
            c.admin_note = note

        db.commit()
        return {"status": "success", "candidate_id": c.id, "new_status": c.status}


def update_candidate_implementation(candidate_id: int, status: str, git_commit: str = None, change_type: str = None, rule_version: str = None, prompt_version: str = None, deployed_at: str = None, implemented_by: str = None) -> Dict[str, Any]:
    """Provides an explicit decoupled engineering implementation tracking loop away from initial logical evaluation."""
    with SessionLocal() as db:
        c = db.query(LearningCandidate).filter_by(id=candidate_id).first()
        if not c:
            return {"error": "Candidate not found"}

        c.implementation_status = status
        if git_commit is not None: c.git_commit_hash = git_commit
        if change_type is not None: c.change_type = change_type
        if rule_version is not None: c.rule_version = rule_version
        if prompt_version is not None: c.prompt_version = prompt_version
        if implemented_by is not None: c.implemented_by = implemented_by

        if deployed_at is not None:
            try:
                c.deployed_at = datetime.fromisoformat(deployed_at.replace('Z', '+00:00'))
            except ValueError:
                pass

        db.commit()
        return {
            "status": "success",
            "candidate_id": c.id,
            "new_implementation_status": c.implementation_status,
            "effectiveness_status": c.effectiveness_status
        }


def evaluate_candidate_impact(candidate_id: int) -> Dict[str, Any]:
    """Triggers the impact evaluation engine computing Pre vs Post arrays mathematically determining effectiveness."""
    from services.learning.metrics import synthesize_windowed_metrics

    with SessionLocal() as db:
        c = db.query(LearningCandidate).filter_by(id=candidate_id).first()
        if not c: return {"error": "Candidate not found"}
        if not c.deployed_at: return {"error": "Candidate lacks a formal deployment date mapping."}

        metrics = synthesize_windowed_metrics(c.rule_id, c.deployed_at, limit_n=50)

        m_pre = metrics.get("pre")
        m_post = metrics.get("post")

        res_obj = {
            "pre_metrics": m_pre,
            "post_metrics": m_post,
            "delta": None
        }

        if m_pre and m_post:
            shift_reject = m_post.get("finding_reject_rate", 0) - m_pre.get("finding_reject_rate", 0)
            shift_truth_contradiction = m_post.get("truth_overturned_rate", 0) - m_pre.get("truth_overturned_rate", 0)

            res_obj["delta"] = {
                "finding_reject_rate_shift": round(shift_reject, 2),
                "truth_contradiction_shift": round(shift_truth_contradiction, 2)
            }

            if shift_reject <= -0.10 or shift_truth_contradiction <= -0.10:
                c.effectiveness_status = "effective"
            elif shift_reject >= +0.10 or shift_truth_contradiction >= +0.10:
                c.effectiveness_status = "ineffective"
            else:
                c.effectiveness_status = "needs_review"

            # Phase 19.5: Variable Cost Model
            volume = m_post.get("count", 0)

            cost_weight = 150.0
            if c.priority_score >= 6.0: cost_weight = 400.0
            elif c.priority_score < 4.0: cost_weight = 50.0

            c_type = str(c.type.value if hasattr(c.type, 'value') else c.type)
            if c_type in ["WORDING_ADJUSTMENT", "TRIAGE_TUNING"]:
                time_weight = 5.0
            elif c_type in ["RECOMMENDATION_TUNING"]:
                time_weight = 15.0
            else:
                time_weight = 30.0

            carrier_multiplier = 1.0
            if c.affected_carriers:
                multipliers = [CARRIER_FRICTION_MAP.get(carr, 1.0) for carr in c.affected_carriers]
                if multipliers:
                    carrier_multiplier = max(multipliers)

            impact_delta = max(0.0, -shift_reject)
            friction_increase = max(0.0, shift_reject)

            estimated_error_reduction = impact_delta * volume
            estimated_time_saved = estimated_error_reduction * time_weight
            financial_impact_estimate = estimated_error_reduction * cost_weight * carrier_multiplier
            friction_cost = friction_increase * volume * cost_weight * carrier_multiplier

            value_score = round(financial_impact_estimate - friction_cost, 2)

            res_obj["value_metrics"] = {
                "estimated_time_saved": round(estimated_time_saved, 2),
                "estimated_error_reduction": round(estimated_error_reduction, 2),
                "financial_impact_estimate": round(financial_impact_estimate, 2),
                "friction_delta": round(shift_reject, 4),
                "value_score": value_score
            }

        c.impact_summary_json = res_obj
        db.commit()

        return {
            "status": "success",
            "candidate_id": c.id,
            "effectiveness_status": c.effectiveness_status,
            "impact_summary": res_obj
        }
