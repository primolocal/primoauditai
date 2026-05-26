"""
Learning — Metrics synthesis and effectiveness analysis.
Extracted from services/learning_service.py
"""
from typing import Dict, List, Any
from collections import Counter
from database.database import SessionLocal
from database.models import FindingReview, AuditRun, ClaimRecord
from schemas import TruthStatusEnum

# Configurable Thresholds
MIN_SAMPLE_SIZE = 10
WARNING_RATE = 0.3
CRITICAL_RATE = 0.5


def synthesize_metrics(test_mode: bool = False, start_time=None, end_time=None) -> Dict[str, Any]:
    """Synthesize advanced approval and rejection telemetry grouped by rule_id."""

    min_n = 2 if test_mode else MIN_SAMPLE_SIZE

    with SessionLocal() as db:
        rev_query = db.query(FindingReview)
        if start_time:
            rev_query = rev_query.filter(FindingReview.created_at >= start_time)
        if end_time:
            rev_query = rev_query.filter(FindingReview.created_at <= end_time)

        reviews = rev_query.all()
        runs = db.query(AuditRun).all()
        claims = db.query(ClaimRecord).all()

        claim_carrier_map = {c.claim_number: c.carrier or "Unknown" for c in claims}

        finding_meta_map = {}
        for run in runs:
            if not run.summary_json: continue
            carrier = claim_carrier_map.get(run.claim_id, "Unknown")
            findings = run.summary_json.get("findings", [])

            audit_meta = {}
            for f in findings:
                audit_meta[f.get("id")] = {
                    "rule_id": f.get("rule_id", "UNKNOWN"),
                    "carrier": carrier
                }
            finding_meta_map[run.audit_id] = audit_meta

        rule_metrics = {}
        carrier_metrics = {}

        for rev in reviews:
            meta = finding_meta_map.get(rev.audit_id, {}).get(rev.finding_id, {})
            rule_id = meta.get("rule_id")
            if not rule_id: continue

            carrier = meta.get("carrier", "Unknown")

            if carrier not in carrier_metrics:
                carrier_metrics[carrier] = {
                    "carrier": carrier,
                    "finding_decisions": 0,
                    "finding_reject_count": 0,
                    "rec_decisions": 0,
                    "rec_reject_count": 0,
                    "truth_both_wrong_missed": 0,
                    "truth_finding_decisions": 0
                }
            c_metrics = carrier_metrics[carrier]

            if rule_id not in rule_metrics:
                rule_metrics[rule_id] = {
                    "rule_id": rule_id,
                    "finding_decisions": 0,
                    "finding_approve_count": 0,
                    "finding_reject_count": 0,
                    "finding_adjust_count": 0,
                    "finding_reasons": Counter(),
                    "rec_decisions": 0,
                    "rec_approve_count": 0,
                    "rec_reject_count": 0,
                    "rec_adjust_count": 0,
                    "rec_reasons": Counter(),
                    "carrier_rejections": Counter(),
                    "recommendation_types": Counter(),
                    "truth_finding_decisions": 0,
                    "truth_finding_validated": 0,
                    "truth_finding_overturned": 0,
                    "truth_sys_correct_rev_wrong": 0,
                    "truth_rev_correct_sys_wrong": 0,
                    "truth_both_wrong_missed": 0,
                    "truth_rec_decisions": 0,
                    "truth_rec_validated": 0,
                    "truth_rec_overturned": 0
                }

            metrics = rule_metrics[rule_id]

            if rev.suggested_action_type:
                metrics["recommendation_types"][rev.suggested_action_type] += 1

            if rev.auditor_outcome:
                metrics["finding_decisions"] += 1
                c_metrics["finding_decisions"] += 1
                if rev.auditor_outcome == "confirm":
                    metrics["finding_approve_count"] += 1
                elif rev.auditor_outcome == "dismiss":
                    metrics["finding_reject_count"] += 1
                    c_metrics["finding_reject_count"] += 1
                    metrics["carrier_rejections"][carrier] += 1
                    if rev.auditor_reason_code:
                        code_str = rev.auditor_reason_code.value if hasattr(rev.auditor_reason_code, 'value') else str(rev.auditor_reason_code)
                        metrics["finding_reasons"][code_str] += 1
                elif rev.auditor_outcome == "edit":
                    metrics["finding_adjust_count"] += 1

            if rev.recommendation_outcome:
                metrics["rec_decisions"] += 1
                c_metrics["rec_decisions"] += 1
                if rev.recommendation_outcome == "confirm":
                    metrics["rec_approve_count"] += 1
                elif rev.recommendation_outcome == "dismiss":
                    metrics["rec_reject_count"] += 1
                    c_metrics["rec_reject_count"] += 1
                    metrics["carrier_rejections"][carrier] += 1
                    if rev.recommendation_reason_code:
                        code_str = rev.recommendation_reason_code.value if hasattr(rev.recommendation_reason_code, 'value') else str(rev.recommendation_reason_code)
                        metrics["rec_reasons"][code_str] += 1
                elif rev.recommendation_outcome == "edit":
                    metrics["rec_adjust_count"] += 1

            if rev.finding_truth_status:
                metrics["truth_finding_decisions"] += 1
                c_metrics["truth_finding_decisions"] += 1
                t_str = rev.finding_truth_status.value if hasattr(rev.finding_truth_status, 'value') else str(rev.finding_truth_status)
                aud_str = rev.auditor_outcome.lower() if rev.auditor_outcome else "open"

                if t_str in ["VALIDATED", "PARTIAL_VALIDATION"]:
                    metrics["truth_finding_validated"] += 1
                    if aud_str in ["dismiss", "edit"]:
                        metrics["truth_sys_correct_rev_wrong"] += 1

                elif t_str == "OVERTURNED":
                    metrics["truth_finding_overturned"] += 1
                    if aud_str in ["dismiss", "edit"]:
                        metrics["truth_rev_correct_sys_wrong"] += 1

                elif t_str == "MISSED_PREVIOUSLY":
                    metrics["truth_finding_overturned"] += 1
                    metrics["truth_both_wrong_missed"] += 1
                    c_metrics["truth_both_wrong_missed"] += 1

            if rev.recommendation_truth_status:
                metrics["truth_rec_decisions"] += 1
                t_str = rev.recommendation_truth_status.value if hasattr(rev.recommendation_truth_status, 'value') else str(rev.recommendation_truth_status)
                if t_str == "VALIDATED": metrics["truth_rec_validated"] += 1
                elif t_str in ["OVERTURNED", "TOO_AGGRESSIVE"]: metrics["truth_rec_overturned"] += 1

        insights = []
        final_metrics = []

        for rule_id, m in rule_metrics.items():
            finding_vars = m["finding_decisions"]
            rec_vars = m["rec_decisions"]

            f_rr = m["finding_reject_count"] / finding_vars if finding_vars > 0 else 0
            r_rr = m["rec_reject_count"] / rec_vars if rec_vars > 0 else 0

            m["finding_reject_rate"] = f_rr
            m["rec_reject_rate"] = r_rr

            if finding_vars >= min_n and f_rr >= WARNING_RATE:
                severity = "critical" if f_rr >= CRITICAL_RATE else "warning"
                insights.append({
                    "rule_id": rule_id,
                    "type": "Logic Drift",
                    "severity": severity,
                    "message": f"Rule logic '{rule_id}' is experiencing a {severity.upper()} rejection rate ({f_rr*100:.1f}%) on its underlying logic firing. ADVISORY ONLY: Please review estimator compliance.",
                    "metrics": m
                })

            if rec_vars >= min_n and r_rr >= WARNING_RATE:
                severity = "critical" if r_rr >= CRITICAL_RATE else "warning"
                insights.append({
                    "rule_id": rule_id,
                    "type": "Action Severity Drift",
                    "severity": severity,
                    "message": f"The proposed Mitigation Penalty for '{rule_id}' is experiencing a {severity.upper()} rejection rate ({r_rr*100:.1f}%) by analysts natively. ADVISORY ONLY: Review the severity configuration.",
                    "metrics": m
                })

            m["finding_reasons"] = dict(m["finding_reasons"].most_common(5))
            m["rec_reasons"] = dict(m["rec_reasons"].most_common(5))
            m["carrier_rejections"] = dict(m["carrier_rejections"].most_common(5))
            m["recommendation_types"] = dict(m["recommendation_types"].most_common(5))

            if finding_vars > 0 or rec_vars > 0:
                final_metrics.append(m)

        return {
            "rule_metrics": final_metrics,
            "insights": insights,
            "carrier_metrics": list(carrier_metrics.values())
        }


def synthesize_hermes_effectiveness() -> Dict[str, Any]:
    """Phase 10: Aggregates Hermes generated logic against reviewer feedback outcomes."""
    from database.models import HermesLog, FindingReview

    with SessionLocal() as db:
        logs = db.query(HermesLog).filter(HermesLog.target_type == "finding").all()
        reviews_list = db.query(FindingReview).all()
        reviews = {r.finding_id: r for r in reviews_list}

        metrics = {}
        vision_stats = {"triggered": 0, "success": 0, "timeout": 0, "failed": 0}

        bkt_base = lambda: {"total": 0, "confirm": 0, "overturn": 0, "review": 0, "validated": 0}
        triage_metrics = {
            "overall": {
                "Address First": bkt_base(),
                "Needs Review": bkt_base(),
                "Request Support": bkt_base(),
                "Low Urgency": bkt_base()
            },
            "carriers": {}
        }

        playbook_metrics = {
            "actions": {},
            "carriers": {}
        }

        for log in logs:
            if log.vision_triggered:
                vision_stats["triggered"] += 1
                if log.vision_success:
                    vision_stats["success"] += 1
                elif log.vision_timeout:
                    vision_stats["timeout"] += 1
                else:
                    vision_stats["failed"] += 1

            template = log.template_family or "unknown"
            variant = log.wording_variant or "unknown"
            carrier = log.carrier or "overall"
            tone = log.advisory_tone or "unknown"

            key = f"{template}_{variant}_{carrier}_{tone}"
            if key not in metrics:
                metrics[key] = {
                    "template_family": template,
                    "wording_variant": variant,
                    "advisory_tone": tone,
                    "carrier": carrier,
                    "total_generated": 0,
                    "accepted": 0,
                    "modified": 0,
                    "rejected": 0,
                    "truth_validated": 0,
                    "truth_overturned": 0,
                    "triage_distribution": {
                        "Address First": 0,
                        "Needs Review": 0,
                        "Request Support": 0,
                        "Low Urgency": 0
                    }
                }

            m = metrics[key]
            m["total_generated"] += 1

            bkt = log.triage_bucket or "Low Urgency"
            if bkt in m["triage_distribution"]:
                m["triage_distribution"][bkt] += 1
            else:
                m["triage_distribution"][bkt] = 1

            rev = reviews.get(log.target_id)
            if rev:
                if rev.recommendation_outcome == "confirm":
                    m["accepted"] += 1
                elif rev.recommendation_outcome == "edit":
                    m["modified"] += 1
                elif rev.recommendation_outcome == "dismiss":
                    m["rejected"] += 1

                if rev.finding_truth_status:
                    t_str = str(rev.finding_truth_status).upper()
                    if "VALID" in t_str:
                        m["truth_validated"] += 1
                    elif "OVERTURNED" in t_str:
                        m["truth_overturned"] += 1

            b_name = log.triage_bucket or "Low Urgency"
            c_name = log.carrier or "overall"
            if c_name not in triage_metrics["carriers"]:
                triage_metrics["carriers"][c_name] = {
                    "Address First": bkt_base(), "Needs Review": bkt_base(),
                    "Request Support": bkt_base(), "Low Urgency": bkt_base()
                }

            triage_metrics["overall"][b_name]["total"] += 1
            triage_metrics["carriers"][c_name][b_name]["total"] += 1

            if rev:
                if rev.recommendation_outcome == "confirm" or log.reviewer_outcome == "confirm":
                    triage_metrics["overall"][b_name]["confirm"] += 1
                    triage_metrics["carriers"][c_name][b_name]["confirm"] += 1
                elif rev.recommendation_outcome == "edit" or log.reviewer_outcome == "edit":
                    triage_metrics["overall"][b_name]["review"] += 1
                    triage_metrics["carriers"][c_name][b_name]["review"] += 1
                elif rev.recommendation_outcome in ["dismiss", "overturn"] or log.reviewer_outcome in ["dismiss", "overturn"]:
                    triage_metrics["overall"][b_name]["overturn"] += 1
                    triage_metrics["carriers"][c_name][b_name]["overturn"] += 1

                if rev.finding_truth_status and "VALID" in str(rev.finding_truth_status).upper():
                    triage_metrics["overall"][b_name]["validated"] += 1
                    triage_metrics["carriers"][c_name][b_name]["validated"] += 1

            p_action = log.primary_action
            if p_action:
                if p_action not in playbook_metrics["actions"]:
                    playbook_metrics["actions"][p_action] = bkt_base()
                playbook_metrics["actions"][p_action]["total"] += 1

                if c_name not in playbook_metrics["carriers"]:
                    playbook_metrics["carriers"][c_name] = {}
                if p_action not in playbook_metrics["carriers"][c_name]:
                    playbook_metrics["carriers"][c_name][p_action] = bkt_base()
                playbook_metrics["carriers"][c_name][p_action]["total"] += 1

                if rev:
                    if rev.recommendation_outcome == "confirm" or log.reviewer_outcome == "confirm":
                        playbook_metrics["actions"][p_action]["confirm"] += 1
                        playbook_metrics["carriers"][c_name][p_action]["confirm"] += 1
                    elif rev.recommendation_outcome == "edit" or log.reviewer_outcome == "edit":
                        playbook_metrics["actions"][p_action]["review"] += 1
                        playbook_metrics["carriers"][c_name][p_action]["review"] += 1
                    elif rev.recommendation_outcome in ["dismiss", "overturn"] or log.reviewer_outcome in ["dismiss", "overturn"]:
                        playbook_metrics["actions"][p_action]["overturn"] += 1
                        playbook_metrics["carriers"][c_name][p_action]["overturn"] += 1
                    if rev.finding_truth_status and "VALID" in str(rev.finding_truth_status).upper():
                        playbook_metrics["actions"][p_action]["validated"] += 1
                        playbook_metrics["carriers"][c_name][p_action]["validated"] += 1

        candidates = []

        metrics_list = list(metrics.values())
        worst_templates = sorted(metrics_list, key=lambda x: (x["modified"] + x["rejected"]) / max(x["total_generated"], 1), reverse=True)[:5]
        best_templates = sorted(metrics_list, key=lambda x: x["accepted"] / max(x["total_generated"], 1), reverse=True)[:5]
        carrier_failures = sorted([m for m in metrics_list if m["carrier"] != "overall" and m["total_generated"] > 0], key=lambda x: (x["rejected"] / x["total_generated"]), reverse=True)[:5]
        logic_correct_we_failed = sorted([m for m in metrics_list if m["truth_validated"] > 0], key=lambda x: (x["rejected"] + x["modified"]) / max(x["total_generated"], 1), reverse=True)[:5]

        return {
            "vision_stats": vision_stats,
            "performance_metrics": metrics_list,
            "triage_metrics": triage_metrics,
            "playbook_metrics": playbook_metrics,
            "new_candidates_generated": len(candidates),
            "reasons": candidates,
            "leaderboards": {
                "worst_templates": worst_templates,
                "best_templates": best_templates,
                "carrier_failures": carrier_failures,
                "logic_correct_wording_rejected": logic_correct_we_failed
            }
        }


def evaluate_truth_preview(claim_id: str, lines: List[Any]) -> Dict[str, Any]:
    """Provides a simulated deterministic line matching mapped to final real world outcomes without DB mutation."""
    with SessionLocal() as db:
        runs = db.query(AuditRun).filter_by(claim_id=claim_id).order_by(AuditRun.created_at.desc()).all()
        if not runs:
            return {"error": "No audit matched for claim", "preview_mapping": []}

        latest_run = runs[0]

        audit_ids = [r.audit_id for r in runs]
        reviews = db.query(FindingReview).filter(FindingReview.audit_id.in_(audit_ids)).all()
        rev_map = {r.finding_id: r for r in reviews}

        base_lines = latest_run.summary_json.get("estimate_info", {}).get("lines", [])
        findings = latest_run.summary_json.get("findings", [])

        line_finding_map = {}
        for f in findings:
            l_nos = f.get("affected_lines", [])
            if not l_nos and f.get("line_no"): l_nos = [f.get("line_no")]
            for ln in l_nos:
                key = str(ln)
                if key not in line_finding_map: line_finding_map[key] = []
                line_finding_map[key].append(f)

        results = []

        for t_line in lines:
            l_id = getattr(t_line, "line_id", t_line.get("line_id", None) if hasattr(t_line, "get") else None)
            part_type = getattr(t_line, "part_type", t_line.get("part_type", None) if hasattr(t_line, "get") else None)
            op_type = getattr(t_line, "operation_type", t_line.get("operation_type", None) if hasattr(t_line, "get") else None)
            desc = getattr(t_line, "description", t_line.get("description", None) if hasattr(t_line, "get") else None)

            matched_line_no = None
            confidence = 0.0
            match_reason = ""

            if l_id is not None:
                exact = next((l for l in base_lines if str(l.get("line_no")) == str(l_id)), None)
                if exact:
                    matched_line_no = str(exact.get("line_no"))
                    confidence = 1.0
                    match_reason = f"Exact line_id match: {l_id}"

            if not matched_line_no and part_type and op_type:
                type_match = next((l for l in base_lines if l.get("part_type") == part_type and l.get("operation_type") == op_type), None)
                if type_match:
                    matched_line_no = str(type_match.get("line_no"))
                    confidence = 0.9
                    match_reason = f"Matched via part_type ({part_type}) and operation_type ({op_type})"

            if not matched_line_no and desc:
                desc_lw = desc.lower()
                desc_match = next((l for l in base_lines if l.get("description") and desc_lw in l.get("description", "").lower()), None)
                if desc_match:
                    matched_line_no = str(desc_match.get("line_no"))
                    confidence = 0.8
                    match_reason = "Matched via description substring overlap"

            if confidence < 0.75:
                continue

            target_findings = line_finding_map.get(matched_line_no, [])

            status_signal = getattr(t_line, "final_carrier_status", t_line.get("final_carrier_status", "") if hasattr(t_line, "get") else "")
            status_signal = (status_signal or "").lower()

            f_truth = "UNRESOLVED"
            if status_signal == "paid_in_full":
                f_truth = "OVERTURNED"
            elif status_signal in ["denied", "reduced"]:
                f_truth = "VALIDATED"
            elif status_signal == "partial":
                f_truth = "PARTIAL_VALIDATION"

            if not target_findings:
                if f_truth in ["VALIDATED", "PARTIAL_VALIDATION"]:
                    results.append({
                        "finding_id": None,
                        "rule_id": "MISSED_ISSUE",
                        "auditor_outcome": None,
                        "suggested_finding_truth": "MISSED_PREVIOUSLY",
                        "discrepancy": "Both Incorrect (Missed Issue)",
                        "confidence": confidence,
                        "match_reason": match_reason
                    })
                continue

            for f in target_findings:
                f_id = f.get("id")
                rev = rev_map.get(f_id)
                aud_outcome = rev.auditor_outcome if rev else "open"

                eval_obj = {
                    "finding_id": f_id,
                    "rule_id": f.get("rule_id", "UNKNOWN"),
                    "auditor_outcome": aud_outcome,
                    "suggested_finding_truth": f_truth,
                    "confidence": confidence,
                    "match_reason": match_reason
                }

                if aud_outcome == "confirm" and f_truth == "OVERTURNED":
                    eval_obj["discrepancy"] = "Both Incorrect (Over-penalized)"
                elif aud_outcome in ["dismiss", "edit"] and f_truth == "OVERTURNED":
                    eval_obj["discrepancy"] = "Reviewer Correct / System Incorrect"
                elif aud_outcome in ["dismiss", "edit"] and f_truth in ["VALIDATED", "PARTIAL_VALIDATION"]:
                    eval_obj["discrepancy"] = "System Correct / Reviewer Incorrect"
                elif aud_outcome == "confirm" and f_truth in ["VALIDATED", "PARTIAL_VALIDATION"]:
                    eval_obj["discrepancy"] = "System Correct & Reviewer Correct"

                results.append(eval_obj)

        return {
            "claim_id": claim_id,
            "preview_mapping": results,
        }


def synthesize_windowed_metrics(rule_id: str, deployed_at, limit_n: int = 50) -> Dict[str, Any]:
    """Slices exactly 50 finding events before deployment, and 50 after deployment for granular impact verifications."""
    with SessionLocal() as db:
        runs = db.query(AuditRun).all()
        reviews = db.query(FindingReview).all()

        finding_meta_map = {}
        for run in runs:
            if not run.summary_json: continue
            findings = run.summary_json.get("findings", [])
            for f in findings:
                if "id" in f:
                    finding_meta_map[f["id"]] = f.get("rule_id", "UNKNOWN")

        target_reviews = [r for r in reviews if finding_meta_map.get(r.finding_id) == rule_id]

        pre_reviews = [r for r in target_reviews if r.created_at < deployed_at]
        post_reviews = [r for r in target_reviews if r.created_at >= deployed_at]

        pre_reviews.sort(key=lambda r: r.created_at, reverse=True)
        pre_reviews = pre_reviews[:limit_n]

        post_reviews.sort(key=lambda r: r.created_at, reverse=False)
        post_reviews = post_reviews[:limit_n]

        def aggregate_metrics(rev_subset):
            finding_decisions = len(rev_subset)
            if finding_decisions == 0: return None

            finding_approve = sum(1 for r in rev_subset if r.auditor_outcome == "confirm")
            finding_reject = sum(1 for r in rev_subset if r.auditor_outcome == "dismiss")
            rec_decisions = sum(1 for r in rev_subset if r.recommendation_outcome)
            rec_approve = sum(1 for r in rev_subset if r.recommendation_outcome == "confirm")
            rec_reject = sum(1 for r in rev_subset if r.recommendation_outcome == "dismiss")

            truth_decisions = sum(1 for r in rev_subset if r.finding_truth_status)
            truth_validated = sum(1 for r in rev_subset if r.finding_truth_status == TruthStatusEnum.VALIDATED)
            truth_overturned = sum(1 for r in rev_subset if r.finding_truth_status == TruthStatusEnum.OVERTURNED)

            return {
                "count": finding_decisions,
                "finding_reject_rate": round(finding_reject / finding_decisions, 2) if finding_decisions else 0,
                "finding_approve_rate": round(finding_approve / finding_decisions, 2) if finding_decisions else 0,
                "rec_reject_rate": round(rec_reject / rec_decisions, 2) if rec_decisions else 0,
                "truth_validated_rate": round(truth_validated / truth_decisions, 2) if truth_decisions else 0,
                "truth_overturned_rate": round(truth_overturned / truth_decisions, 2) if truth_decisions else 0,
            }

        return {
            "pre": aggregate_metrics(pre_reviews),
            "post": aggregate_metrics(post_reviews)
        }
