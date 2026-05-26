"""
Learning — Finding enrichment and recommendation calibration.
Extracted from services/learning_service.py
"""
from datetime import datetime
from typing import Dict, List, Any

from database.database import SessionLocal
from database.models import AuditRun, FindingReview, ClaimRecord


def get_claim_history(claim_id: str) -> Dict[str, Any]:
    """Phase 6: Retrieves a specific claim's intelligence history across all prior nested Audits."""
    with SessionLocal() as db:
        runs = db.query(AuditRun).filter_by(claim_id=claim_id).order_by(AuditRun.created_at.asc()).all()
        if not runs:
            return {"error": f"No audit history found for claim {claim_id}"}

        claim_rec = db.query(ClaimRecord).filter_by(claim_number=claim_id).first()
        resolved_carrier = claim_rec.carrier if claim_rec and claim_rec.carrier else (runs[0].carrier if runs[0].carrier else "Unknown")

        history = {
            "claim_number": claim_id,
            "carrier": resolved_carrier,
            "prior_audit_count": len(runs),
            "prior_revision_count": 0,
            "timeline": [],
            "indicators": {
                "previously_validated": 0,
                "previously_overturned": 0,
                "recommendation_too_aggressive": 0,
                "missed_issue_found_later": 0
            }
        }

        for index, r in enumerate(runs):
            reviews = db.query(FindingReview).filter_by(audit_id=r.audit_id).all()

            event_type = "Initial Audit" if index == 0 else "Supplement / Carrier Revision"

            validated_count = 0
            overturned_count = 0
            rec_aggressive = 0

            for rev in reviews:
                if hasattr(rev, 'finding_truth_status') and rev.finding_truth_status:
                    if rev.finding_truth_status.name == 'VALIDATED' or rev.finding_truth_status == 'VALIDATED':
                        validated_count += 1
                        history["indicators"]["previously_validated"] += 1
                    elif rev.finding_truth_status.name in ['OVERTURNED', 'PARTIAL_VALIDATION'] or rev.finding_truth_status in ['OVERTURNED', 'PARTIAL_VALIDATION']:
                        overturned_count += 1
                        history["indicators"]["previously_overturned"] += 1

                if hasattr(rev, 'recommendation_truth_status') and rev.recommendation_truth_status:
                    if rev.recommendation_truth_status.name == 'OVERTURNED' or rev.recommendation_truth_status == 'OVERTURNED':
                        rec_aggressive += 1
                        history["indicators"]["recommendation_too_aggressive"] += 1

                if hasattr(rev, "is_unresolved_override") and rev.is_unresolved_override:
                    history["prior_revision_count"] += 1

            history["timeline"].append({
                "audit_id": r.audit_id,
                "event": event_type,
                "date": r.created_at.isoformat(),
                "findings_count": len(reviews),
                "truth_summary": {
                    "validated": validated_count,
                    "overturned": overturned_count,
                    "rec_overturned": rec_aggressive
                }
            })

        # Phase 6 Enhancement: Compute operational risk flags natively (Ratio-Aware)
        risk_flags = []

        total_historical_findings = sum(t["findings_count"] for t in history["timeline"])
        total_validated = history["indicators"]["previously_validated"]
        total_overturned = history["indicators"]["previously_overturned"]
        total_aggressive = history["indicators"]["recommendation_too_aggressive"]

        if history["prior_revision_count"] > 0 and len(history["timeline"]) >= 3:
            risk_flags.append("high_revision_claim")

        if total_overturned >= 2 and total_historical_findings > 0:
            if (total_overturned / total_historical_findings) > 0.30:
                risk_flags.append("high_overturn_rate")

        if total_aggressive >= 1 and total_validated > 0:
            if (total_aggressive / total_validated) > 0.25:
                risk_flags.append("recommendation_risk")

        history["risk_flags"] = risk_flags

        return history


def enrich_active_findings_with_signals(
    active_findings: list,
    full_audit_payload: dict,
    claim_id: str,
    current_audit_id: str,
    current_carrier: str = None
) -> None:
    """Phase 6.5 & 7: Augments active findings list with historical_signals natively matched across prior claims & carriers."""
    if not claim_id:
        return

    with SessionLocal() as db:
        claim_runs = db.query(AuditRun).filter(AuditRun.claim_id == claim_id, AuditRun.audit_id != current_audit_id).all()

        carrier_runs = []
        if current_carrier:
            carrier_claims = db.query(ClaimRecord).filter(ClaimRecord.carrier == current_carrier, ClaimRecord.claim_number != claim_id).all()
            c_ids = [c.claim_number for c in carrier_claims]
            if c_ids:
                carrier_runs = db.query(AuditRun).filter(AuditRun.claim_id.in_(c_ids)).order_by(AuditRun.created_at.desc()).limit(200).all()

        if not claim_runs and not carrier_runs:
            return

        def build_hist_meta(runs_list):
            meta = {}
            now = datetime.utcnow()
            for r in runs_list:
                if not r.summary_json: continue
                hist_est_lines = r.summary_json.get("estimate_lines", {}).get("items", [])
                hist_lines_by_no = {ln.get("line_no"): ln for ln in hist_est_lines}

                reviews = db.query(FindingReview).filter_by(audit_id=r.audit_id).all()
                review_dict = {rev.finding_id: rev for rev in reviews}

                run_age_days = (now - r.created_at).days if r.created_at else 0

                for hf in r.summary_json.get("findings", []):
                    fid = hf.get("id")
                    h_rev = review_dict.get(fid)
                    if not h_rev: continue

                    part_types = set()
                    op_types = set()
                    descriptions = []

                    for line_no in hf.get("affected_lines", []):
                        ln = hist_lines_by_no.get(line_no, {})
                        if ln.get("part_type"): part_types.add(ln.get("part_type"))
                        if ln.get("operation_type"): op_types.add(ln.get("operation_type"))
                        if ln.get("description"): descriptions.append(str(ln.get("description")).lower())
                    meta[fid] = {
                        "event_age_days": run_age_days,
                        "part_types": part_types,
                        "op_types": op_types,
                        "descriptions": descriptions,
                        "f_status": getattr(h_rev, 'finding_truth_status', None),
                        "r_status": getattr(h_rev, 'recommendation_truth_status', None)
                    }
            return meta

        claim_meta = build_hist_meta(claim_runs)
        carrier_meta = build_hist_meta(carrier_runs)

        active_est_lines = full_audit_payload.get("estimate_lines", {}).get("items", [])
        active_lines_by_no = {ln.get("line_no"): ln for ln in active_est_lines}

        for af in active_findings:
            af["historical_signals"] = []
            a_part_types = set()
            a_op_types = set()
            a_desc = []

            for line_no in af.get("affected_lines", []):
                ln = active_lines_by_no.get(line_no, {})
                if ln.get("part_type"): a_part_types.add(ln.get("part_type"))
                if ln.get("operation_type"): a_op_types.add(ln.get("operation_type"))
                if ln.get("description"): a_desc.append(str(ln.get("description")).lower())

            def check_match(meta_dict):
                stats = {
                    "has_overturned": False,
                    "has_rejected_rec": False,
                    "has_validated": False,
                    "best_conf": 0.0,
                    "min_age_days": 9999,
                    "match_count": 0,
                    "validated_count": 0,
                    "overturned_count": 0,
                    "recommendation_reject_count": 0
                }

                for hf_id, meta in meta_dict.items():
                    matched = False
                    conf = 0.0
                    if meta["part_types"] and meta["part_types"].intersection(a_part_types) and \
                       meta["op_types"] and meta["op_types"].intersection(a_op_types):
                        matched = True
                        conf = 1.0
                    else:
                        for d_a in a_desc:
                            for d_h in meta["descriptions"]:
                                a_tok = set(d_a.split())
                                h_tok = set(d_h.split())
                                if len(a_tok.intersection(h_tok)) >= 2:
                                    matched = True
                                    conf = 0.8
                                    break
                            if matched: break

                    if matched:
                        stats["match_count"] += 1
                        stats["best_conf"] = max(stats["best_conf"], conf)
                        stats["min_age_days"] = min(stats["min_age_days"], meta["event_age_days"])

                        fts = meta["f_status"]
                        rts = meta["r_status"]
                        f_name = fts.name if hasattr(fts, 'name') else fts
                        r_name = rts.name if hasattr(rts, 'name') else rts

                        if f_name in ['OVERTURNED', 'PARTIAL_VALIDATION']:
                            stats["has_overturned"] = True
                            stats["overturned_count"] += 1
                        if r_name == 'OVERTURNED':
                            stats["has_rejected_rec"] = True
                            stats["recommendation_reject_count"] += 1
                        if f_name == 'VALIDATED':
                            stats["has_validated"] = True
                            stats["validated_count"] += 1

                return stats

            claim_stats = check_match(claim_meta)
            carr_stats = check_match(carrier_meta)

            def build_signal_obj(signal_type, source, baseweight, reason, stats):
                age = stats["min_age_days"] if stats["min_age_days"] != 9999 else 0
                rec_multi = 1.0
                if age > 180: rec_multi = 0.4
                elif age > 90: rec_multi = 0.6
                elif age > 30: rec_multi = 0.8

                eff_weight = baseweight * stats["best_conf"] * rec_multi

                return {
                    "type": signal_type,
                    "source": source,
                    "weight": baseweight,
                    "reason": reason,
                    "match_confidence": stats["best_conf"],
                    "event_age_days": age,
                    "recency_multiplier": rec_multi,
                    "match_count": stats["match_count"],
                    "validated_count": stats["validated_count"],
                    "overturned_count": stats["overturned_count"],
                    "recommendation_reject_count": stats["recommendation_reject_count"],
                    "effective_weight": round(eff_weight, 2)
                }

            signals = []

            if claim_stats["has_overturned"]:
                signals.append(build_signal_obj("historically_overturned", "finding", 1.0, "Similar findings overturned previously on this claim.", claim_stats))
            if claim_stats["has_rejected_rec"]:
                signals.append(build_signal_obj("recommendation_risk", "finding", 1.0, "Recommendations for this pattern are notoriously rejected on this claim.", claim_stats))
            if claim_stats["has_validated"]:
                signals.append(build_signal_obj("historically_validated", "finding", 1.0, "Historically validated pattern by guidelines.", claim_stats))

            if carr_stats["has_overturned"] and not claim_stats["has_overturned"]:
                signals.append(build_signal_obj("carrier_historically_overturned", "carrier", 0.6, "Similar findings previously overturned for this carrier.", carr_stats))
            if carr_stats["has_rejected_rec"] and not claim_stats["has_rejected_rec"]:
                signals.append(build_signal_obj("carrier_recommendation_risk", "carrier", 0.6, "Recommendations for this carrier frequently rejected.", carr_stats))
            if carr_stats["has_validated"] and not claim_stats["has_validated"]:
                signals.append(build_signal_obj("carrier_historically_validated", "carrier", 0.6, "Historically validated pattern for this carrier.", carr_stats))

            af["historical_signals"] = signals


def calibrate_recommendations(active_findings: list) -> None:
    """Phase 8: Maps recommendation strength deterministically against evidence and historical signals."""
    for af in active_findings:
        base_conf = float(af.get("confidence", 100))
        if base_conf <= 1.0: base_conf *= 100

        score = int(base_conf)
        reasons = []

        evidence_refs = af.get("evidence_refs", [])
        has_missing_evidence = any(e.get("support_status") == "missing" for e in evidence_refs)
        if has_missing_evidence:
            score -= 20
            reasons.append("-20: Missing explicitly required photographic evidence")

        signals = af.get("historical_signals") or []
        for s in signals:
            t = s.get("type", "")
            if t in ["historically_overturned", "carrier_historically_overturned"]:
                score -= 30
                reasons.append(f"-30: High override rate identified natively ({t.replace('_', ' ') })")
            elif t in ["recommendation_risk", "carrier_recommendation_risk"]:
                score -= 20
                reasons.append(f"-20: Frequent logic rejection by manual reviewers ({t.replace('_', ' ')})")
            elif t in ["historically_validated", "carrier_historically_validated"]:
                score += 20
                reasons.append(f"+20: Active validation track record recognized")

        if score < 0: score = 0
        if score > 100: score = 100

        af["recommendation_strength_score"] = score

        if score < 40:
            af["recommendation_strength"] = "soft_caution"
            af["calibrated_action_text"] = "Estimator note review occasionally useful. No harsh overrides default."
        elif score <= 65:
            af["recommendation_strength"] = "request_support"
            af["calibrated_action_text"] = "Request supporting invoice/documentation. Do not strictly reject."
        elif score <= 85:
            af["recommendation_strength"] = "review_required"
            af["calibrated_action_text"] = "Strong discrepancy. Immediate manual exception review highly suggested."
        else:
            af["recommendation_strength"] = "strong_challenge"
            af["calibrated_action_text"] = "Clear guideline violation. Confident revision challenge supported natively."

        af["calibration_reasons"] = reasons
