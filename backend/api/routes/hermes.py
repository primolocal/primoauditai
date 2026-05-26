"""
Hermes routes — retry and mock advisory endpoints.
"""
import uuid
import os
from datetime import datetime
import httpx

from fastapi import APIRouter, HTTPException

from schemas import HermesAdvisoryPayload

hermes_router = APIRouter(prefix="/api", tags=["hermes"])


@hermes_router.post("/audits/{audit_id}/retry-hermes")
async def retry_hermes(audit_id: str):
    from storage.review_repository import SQLReviewRepository
    repo = SQLReviewRepository()

    run = repo.get_audit_run(audit_id)
    if not run:
        raise HTTPException(status_code=404, detail="AuditRun not found")

    if run.get("ingestion_status") != "normalized":
        raise HTTPException(status_code=400, detail="Audit Run is not normalized. Cannot run Hermes.")

    if run.get("hermes_status") == "processing":
        raise HTTPException(status_code=409, detail="A Hermes refresh is already in progress.")

    # 1. Versioning: Archiving the old run_id
    old_run_id = run.get("run_id")
    prev_runs = run.get("previous_runs", [])
    if old_run_id and old_run_id not in prev_runs:
        prev_runs.append(old_run_id)
    run["previous_runs"] = prev_runs

    # 2. Assigning the new run_id
    new_run_id = f"aud_{uuid.uuid4().hex[:8]}"
    run["run_id"] = new_run_id
    run["hermes_status"] = "processing"

    # Pre-save to lock state out from concurrent calls immediately
    repo.save_audit_run(audit_id, run)

    base_vps_url = os.getenv("HERMES_VPS_URL", "").rstrip('/')
    if not base_vps_url:
        raise HTTPException(status_code=503, detail="Hermes service not configured")
    hermes_url = f"{base_vps_url}/webhooks/audit_trigger"

    try:
        started_at = datetime.utcnow()

        claim_pkg = run.get("claim_package", {})
        est_summary = run.get("estimate_lines", {}).get("summary", {})
        ev_matrix = run.get("evidence_matrix", {})

        photos = ev_matrix.get("photos", [])
        documents = ev_matrix.get("documents", [])
        mappings = ev_matrix.get("line_mappings", {})

        photos_count = len(photos)
        pdf_count = len(documents)

        req_payload = {
            "claim_id": claim_pkg.get("claim_number", "UNKNOWN"),
            "event_type": "audit_start",
            "audit_id": audit_id,
            "estimate_type": "supplement" if "-S" in (run.get("active_supplement") or "") else "original",
            "carrier": claim_pkg.get("carrier", "UNKNOWN"),
            "state": claim_pkg.get("state", "UNKNOWN"),
            "scope": run.get("active_supplement") or "E01",
            "data": {
                "facts_of_loss": claim_pkg.get("facts_of_loss", "Not provided."),
                "estimate_summary": {
                    "gross_total": float(est_summary.get("gross_total", 0.0) or 0.0),
                    "labor_hours": float(est_summary.get("total_labor_hours", 0.0) or 0.0),
                    "labor_days": int(est_summary.get("repair_days", 0) or 0)
                },
                "estimate_lines": run.get("estimate_lines", {}).get("items", []),
                "evidence": {
                    "photos_count": photos_count,
                    "pdf_count": pdf_count,
                    "photo_metadata": photos,
                    "document_metadata": documents,
                    "photo_line_mappings": mappings
                },
                "validation_signals": {
                    "ems_verified": True,
                    "evidence_mapped": (photos_count + pdf_count) > 0
                },
                "deterministic_findings": run.get("findings", [])
            }
        }

        import json

        # 1. Explicitly serialize the JSON with no spaces so we control it
        payload_bytes = json.dumps(req_payload, separators=(',', ':')).encode('utf-8')

        # 2. Hash those exact bytes using the secure function
        from security import sign_webhook_payload
        signature = sign_webhook_payload(payload_bytes)

        # 3. Set headers explicitly
        headers = {
            "x-hermes-event": "audit_start",
            "Content-Type": "application/json",
            "Content-Length": str(len(payload_bytes)),
            "x-hub-signature-256": signature
        }

        # 4. Send the physical bytes natively via httpx
        with httpx.Client() as client:
            resp = client.post(hermes_url, content=payload_bytes, headers=headers, timeout=180.0)

        completed_at = datetime.utcnow()
        elapsed_ms = int((completed_at - started_at).total_seconds() * 1000)

        resp.raise_for_status()

        h_data = resp.json()

        tasks = h_data.get("tasks", {})
        tasks_list = tasks.get("tasks", []) if isinstance(tasks, dict) else []

        if len(tasks_list) == 0:
             raise ValueError("Hermes payload returned 0 executable tasks.")

        # 3. Clean Override (No Appending)
        run["hermes_tasks"] = tasks
        run["findings"] = h_data.get("findings", [])
        run["rule_results"] = h_data.get("rule_results", [])
        run["scorecard"] = h_data.get("scorecard", {})
        run["narrative"] = h_data.get("narrative", {})
        run["hermes_advisory"] = h_data.get("hermes_advisory", {})

        run["hermes_status"] = "success"
        run["manual_review_mode"] = False
        run.pop("hermes_failure_metadata", None)

        run["hermes_run_metadata"] = {
            "hermes_run_id": new_run_id,
            "hermes_status": "success",
            "hermes_started_at": started_at.isoformat() + "Z",
            "hermes_completed_at": completed_at.isoformat() + "Z",
            "hermes_elapsed_ms": elapsed_ms,
            "hermes_error_code": None,
            "hermes_error_message": None
        }

        if "activity_log" in run:
            run["activity_log"].append({
                "id": f"evt_{uuid.uuid4().hex[:6]}",
                "timestamp": completed_at.isoformat() + "Z",
                "actor": "auditor",
                "event_type": "hermes_retry",
                "description": f"Hermes Intelligence Engine manual refresh succeeded in {elapsed_ms}ms. (Run {new_run_id})"
            })

        repo.save_audit_run(audit_id, run)
        return run

    except Exception as e:
        completed_at = datetime.utcnow()
        safe_started = locals().get('started_at', datetime.utcnow())
        elapsed_ms = int((completed_at - safe_started).total_seconds() * 1000)

        error_code = "unknown_error"
        message = str(e)
        if isinstance(e, httpx.TimeoutException):
            error_code = "timeout"
        elif isinstance(e, httpx.RequestError):
            error_code = "connection_error"
        elif isinstance(e, httpx.HTTPStatusError):
            status_code = getattr(e.response, "status_code", 500) if hasattr(e, "response") else 500
            error_code = "5xx" if status_code >= 500 else "invalid_request"
        elif getattr(e, "__class__", None).__name__ == "JSONDecodeError" or isinstance(e, ValueError):
            error_code = "invalid_response_schema"

        run["hermes_status"] = "failed"
        run["manual_review_mode"] = True
        run.pop("hermes_failure_metadata", None)

        run["hermes_run_metadata"] = {
            "hermes_run_id": new_run_id,
            "hermes_status": "failed",
            "hermes_started_at": safe_started.isoformat() + "Z",
            "hermes_completed_at": completed_at.isoformat() + "Z",
            "hermes_elapsed_ms": elapsed_ms,
            "hermes_error_code": error_code,
            "hermes_error_message": message
        }

        # Ensure valid empty response shapes
        run["hermes_tasks"] = {"tasks": [], "total_tasks": 0, "resolved_tasks": 0}
        run["findings"] = []
        run["scorecard"] = {"overall_score": 100, "verdict": "Pass", "category_scores": {}}

        if "activity_log" in run:
            run["activity_log"].append({
                "id": f"evt_{uuid.uuid4().hex[:6]}",
                "timestamp": completed_at.isoformat() + "Z",
                "actor": "system",
                "event_type": "hermes_failure",
                "description": f"Hermes Intelligence Engine refresh failed: {error_code}. Fallback to manual review mode enforced."
            })

        repo.save_audit_run(audit_id, run)

        raise HTTPException(status_code=500, detail=f"Hermes refresh failed: {str(e)}")


@hermes_router.post("/hermes/advisory")
async def mock_remote_hermes_advisory(payload: HermesAdvisoryPayload):
    """
    Simulates the detached Hermes API cluster responding to a strict payload format with isolated advisory blocks.
    In production, this lives on a physically separate server/service.
    """
    out_findings = []

    for f in payload.findings:
        sev = f.get("severity", 0)
        rule = f.get("rule_id", "General")

        # Simulate an LLM parsing logic based purely on input strings
        if sev > 25 or "labor" in rule.lower():
            escalation = "review"
            conf = "high"
            action = "Verify labor rates carefully."
            tip = "Historically, estimators pad labor on this specific part."
            adv = f"Hermes Context: Given the severity, a physical review is recommended. Trust but verify."
        else:
            escalation = "none"
            conf = "medium"
            action = "Standard progression."
            tip = "No advanced telemetry flags."
            adv = "Hermes Context: Finding appears standard and non-contentious."

        out_findings.append({
            "finding_id": f.get("id"),
            "advisory": adv,
            "confidence": conf,
            "escalation": escalation,
            "recommended_action": action,
            "coaching_tip": tip
        })

    return {
        "audit_summary": f"Hermes generated advisory for {len(payload.findings)} deterministic findings via decoupled orchestration.",
        "findings": out_findings
    }
