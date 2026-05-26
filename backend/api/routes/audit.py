"""
Audit routes — upload, run, status, GET, findings, scores, narratives,
finding update, review-state, finding-review, asset-verdict, activity, vision,
QC endpoint, analytics, claim history, extract-photos.
"""
import io
import os
import sys
import uuid
import base64 as _b64
import json as _json
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, UploadFile, File, HTTPException, Request, Form, BackgroundTasks

# Ensure the backend directory is in the path to load local modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from security import validate_upload_size, validate_zip_bomb
from logging_config import get_logger, set_correlation_id
from schemas import (
    ActionPayload, FindingReviewPayload, AssetVerdictPayload,
    ActivityEventPayload,
)

logger = get_logger("primoaudit.api")

audit_router = APIRouter(prefix="/api", tags=["audit"])

# Shared repo instance
from storage.review_repository import SQLReviewRepository
repo = SQLReviewRepository()


@audit_router.post("/extract-photos")
async def extract_photos(photos: UploadFile = File(...)):
    """Extract images from a PDF file and return as base64 data URLs."""
    try:
        import fitz
        contents = await photos.read()
        doc = fitz.open(stream=contents, filetype="pdf")
        extracted = []
        for page_num in range(len(doc)):
            for img in doc[page_num].get_images():
                xref = img[0]
                base_image = doc.extract_image(xref)
                extracted.append({
                    "filename": f"{photos.filename}_p{page_num+1}_{xref}.jpg",
                    "data_url": f"data:image/jpeg;base64,{_b64.b64encode(base_image['image']).decode()}",
                })
        doc.close()
        return {"photos": extracted, "count": len(extracted)}
    except Exception as e:
        return {"photos": [], "count": 0, "error": str(e)}


# Phase 22: Hermes Integration Mock Server is now in api/routes/hermes.py


@audit_router.post("/audit/run")
@audit_router.post("/audits")
async def run_audit_live(
    request: Request,
    background_tasks: BackgroundTasks,
    ems_zip: UploadFile = File(...),
    supporting_files: List[UploadFile] = File(default=[]),
    evidence_mode: str = Form("live")
):
    request_id = getattr(request.state, "request_id", "unknown")
    set_correlation_id(request_id)

    if not ems_zip.filename.lower().endswith('.zip'):
        raise HTTPException(status_code=400, detail="ems_zip must be a single .zip file.")

    contents = await ems_zip.read()

    # --- Enterprise Validation ---
    validate_upload_size(contents, ems_zip.filename)
    validate_zip_bomb(contents)

    logger.info(
        f"Audit upload: file={ems_zip.filename}, size={len(contents)}B, "
        f"support_files={len(supporting_files)}, evidence_mode={evidence_mode}"
    )

    # Pre-generate IDs
    job_id = f"job_{uuid.uuid4().hex[:8]}"
    run_id = f"aud_{uuid.uuid4().hex[:8]}"

    # Process supporting files into byte tuples
    sf_tuples = []
    for sf in supporting_files:
        if sf.filename:
            sf_bytes = await sf.read()
            sf_tuples.append((sf.filename, sf_bytes))

    # Initialize DB processing state
    repo.create_job(job_id=job_id, audit_id=run_id)

    base_url = str(request.base_url).rstrip("/")

    # Fire and Forget
    from pipeline_worker import process_audit_pipeline
    background_tasks.add_task(
        process_audit_pipeline,
        job_id,
        run_id,
        contents,
        sf_tuples,
        evidence_mode,
        base_url
    )

    return {
        "job_id": job_id,
        "run_id": run_id,
        "audit_id": run_id,
        "status": "processing",
        "progress": 0,
        "message": "Enqueued extraction job"
    }


@audit_router.get("/audits/{audit_id}/status")
async def get_audit_job_status(audit_id: str):
    from database.models import ProcessingJob
    from database.database import SessionLocal
    with SessionLocal() as session:
        job = session.query(ProcessingJob).filter_by(audit_id=audit_id).order_by(ProcessingJob.id.desc()).first()
        if job:
            return {"job_id": job.job_id, "status": job.status, "progress": job.progress_percentage, "message": job.message}
        return {"status": "completed"}


@audit_router.get("/audit/{audit_id}/review-state")
async def get_review_state(audit_id: str):
    return repo.get_review_state(audit_id)


@audit_router.post("/audit/{audit_id}/finding-review")
async def set_finding_review(audit_id: str, payload: FindingReviewPayload):
    updated_notes = repo.set_finding_review(
        audit_id,
        payload.finding_id,
        payload.note,
        payload.health_status,
        payload.health_explanation,
        evidence_exists=payload.evidence_exists,
        evidence_uploaded=payload.evidence_uploaded,
        linked_asset_ids=payload.linked_asset_ids,
        missing_upload_reason=payload.missing_upload_reason,
        hermes_critique=payload.hermes_critique,
        auditor_outcome=payload.auditor_outcome,
        auditor_reason_code=payload.auditor_reason_code,
        guideline_citation=payload.guideline_citation
    )
    return {"status": "ok", "reviewer_notes": updated_notes}


@audit_router.post("/audit/{audit_id}/asset-verdict")
async def set_asset_verdict(audit_id: str, payload: AssetVerdictPayload):
    updated_verdicts = repo.set_asset_verdict(
        audit_id,
        payload.state_key,
        payload.verdict
    )
    return {"status": "ok", "asset_verdicts": updated_verdicts}


def _ensure_hermes_finalized(run: dict, audit_id: str) -> None:
    """Finalize Hermes enrichment on an audit run if it hasn't been done yet.

    Called by GET endpoints that serve the audit payload.  Only runs once —
    subsequent calls detect ``hermes_finalized`` and skip the work.
    """
    from services.hermes_orchestrator import CURRENT_HERMES_VERSION

    claim_id = run.get("claim_package", {}).get("claim_number")
    carrier = run.get("claim_package", {}).get("carrier")
    is_hermes_current = (
        run.get("hermes_finalized")
        and run.get("hermes_version_applied") == CURRENT_HERMES_VERSION
    )

    if not claim_id or is_hermes_current:
        return

    from services.learning_service import LearningService
    from services.hermes_orchestrator import finalize_audit_advisory

    findings = run.get("findings", [])
    LearningService.enrich_active_findings_with_signals(findings, run, str(claim_id), audit_id, carrier)
    LearningService.calibrate_recommendations(findings)
    finalize_audit_advisory(run, findings)
    repo.save_audit_run(audit_id, run)

    # Phase 20B: Dynamic Coaching Context Injection (Flyweight, Non-Persistent)
    auditor = run.get("auditor_id")
    if auditor:
        from services.coaching_service import CoachingService
        for f in findings:
            prompts = CoachingService.get_contextual_prompts(auditor, f, carrier)
            if prompts:
                f["coaching_prompts"] = prompts

    # Phase 22: Remote Hermes Advisory Injection
    if "hermes_advisory" not in run:
        from services.hermes_advisory_service import HermesAdvisoryService
        advisory_data = HermesAdvisoryService.fetch_audit_advisory(run)
        run["hermes_advisory"] = advisory_data
        repo.save_audit_run(audit_id, run)

    # Phase 23: Pre-Submission Risk Engine
    from services.dispute_service import DisputeSimulationService
    dispute_modified = False
    for f in findings:
        if "dispute_risk" not in f:
            f["dispute_risk"] = DisputeSimulationService.calculate_dispute_risk(f, carrier)
            dispute_modified = True
    if dispute_modified:
        repo.save_audit_run(audit_id, run)


@audit_router.get("/audits/{audit_id}")
async def get_audit(audit_id: str):
    run = repo.get_audit_run(audit_id)
    if not run:
        raise HTTPException(status_code=404, detail="AuditRun not found")

    _ensure_hermes_finalized(run, audit_id)
    return run


@audit_router.get("/audits/{audit_id}/findings")
async def get_audit_findings(audit_id: str):
    run = repo.get_audit_run(audit_id)
    if not run:
        raise HTTPException(status_code=404, detail="AuditRun not found")

    _ensure_hermes_finalized(run, audit_id)
    return run.get("findings", [])


@audit_router.get("/audits/{audit_id}/score")
async def get_audit_score(audit_id: str):
    run = repo.get_audit_run(audit_id)
    if not run:
        raise HTTPException(status_code=404, detail="AuditRun not found")
    return run.get("scorecard", {})


@audit_router.get("/audits/{audit_id}/narrative")
async def get_audit_narrative(audit_id: str):
    run = repo.get_audit_run(audit_id)
    if not run:
        raise HTTPException(status_code=404, detail="AuditRun not found")
    return run.get("narrative", {})


@audit_router.post("/audits/{audit_id}/activity")
async def log_audit_activity(audit_id: str, payload: ActivityEventPayload):
    audit_run = repo.get_audit_run(audit_id)
    if not audit_run:
        raise HTTPException(status_code=404, detail="AuditRun not found")

    act_evt = {
        "id": f"evt_{uuid.uuid4().hex[:6]}",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "actor": "auditor",
        "event_type": payload.event_type,
        "description": payload.description,
        "metadata_context": payload.metadata_context or {}
    }

    activity_log = audit_run.setdefault("activity_log", [])
    activity_log.append(act_evt)
    repo.save_audit_run(audit_id, audit_run)

    return {"status": "success", "event_id": act_evt["id"]}


@audit_router.post("/audits/{audit_id}/findings/{finding_id}/{action}")
async def update_finding(audit_id: str, finding_id: str, action: str, background_tasks: BackgroundTasks, payload: ActionPayload = ActionPayload()):
    audit_run = repo.get_audit_run(audit_id)
    if not audit_run:
        raise HTTPException(status_code=404, detail="AuditRun not found")

    findings = audit_run.get("findings", [])

    target_f = next((f for f in findings if f.get("id") == finding_id), None)
    if not target_f:
        raise HTTPException(status_code=404, detail="Finding not found")

    evt_type = ""
    # Map API action to Hermes Feedback action
    hermes_action = action
    if action == "confirm":
        target_f["status"] = "confirmed"
        evt_type = "finding_confirmed"
        repo.set_finding_review(
            audit_id, finding_id,
            triage_bucket=target_f.get("triage_bucket")
        )
    elif action == "overturn":
        target_f["status"] = "overturned"
        evt_type = "finding_overturned"
        hermes_action = "dismiss"
        repo.set_finding_review(
            audit_id, finding_id,
            triage_bucket=target_f.get("triage_bucket")
        )
    elif action == "recommendation_feedback":
        target_f["recommendation_outcome"] = payload.recommendation_outcome
        target_f["recommendation_reason_code"] = payload.recommendation_reason
        evt_type = "recommendation_feedback_submitted"
        hermes_action = payload.recommendation_outcome or "feedback"
        repo.set_finding_review(
            audit_id, finding_id,
            recommendation_outcome=payload.recommendation_outcome,
            recommendation_reason_code=payload.recommendation_reason,
            triage_bucket=target_f.get("triage_bucket")
        )
    else:
        raise HTTPException(status_code=400, detail="Invalid action")

    # Phase 28: Decoupled Hermes Learning Loop
    def trigger_hermes_feedback():
        import httpx
        try:
            req_payload = {
                "audit_id": audit_id,
                "finding_id": finding_id,
                "rule_id": target_f.get("rule_id", "UNKNOWN"),
                "action": hermes_action,
                "context": {
                    "reason_code": payload.reason_code,
                    "target_action": action,
                    "recommendation_outcome": payload.recommendation_outcome
                }
            }
            httpx.post("http://127.0.0.1:8000/hermes/feedback", json=req_payload, timeout=5.0)
        except Exception as e:
            logger.warning(f"[Hermes] Failed to emit feedback webhook: {e}")

    background_tasks.add_task(trigger_hermes_feedback)

    act_evt = {
        "id": f"evt_{uuid.uuid4().hex[:6]}",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "actor": "auditor",
        "event_type": evt_type,
        "description": f"Auditor {action}ed finding {target_f.get('rule_id')}.",
        "metadata_context": {
            "finding_id": finding_id,
            "reason_code": payload.reason_code,
            "comment": payload.comment,
            "recommendation_outcome": payload.recommendation_outcome,
            "recommendation_reason": payload.recommendation_reason
        }
    }
    activity_log = audit_run.setdefault("activity_log", [])
    activity_log.append(act_evt)

    from scoring import ScoringService
    from narrative import NarrativeService
    from schemas import Scorecard, CategoryScores

    score_data = ScoringService.calculate(findings)
    new_cat_scores = score_data.get("category_scores", {})

    new_scorecard = Scorecard(
        overall_score=score_data.get("score", 100),
        verdict=score_data.get("verdict", "Pass"),
        category_scores=CategoryScores(
            structural_integrity=new_cat_scores.get("structural_integrity", 100),
            line_item_support=new_cat_scores.get("line_item_support", 100),
            parts_accuracy=new_cat_scores.get("parts_accuracy", 100),
            labor_reasonableness=new_cat_scores.get("labor_reasonableness", 100),
            documentation_readiness=new_cat_scores.get("documentation_readiness", 100),
            rules_compliance=new_cat_scores.get("rules_compliance", 100),
            carrier_compliance=new_cat_scores.get("carrier_compliance", 100)
        )
    ).model_dump()

    audit_run["scorecard"] = new_scorecard

    narrative_data = NarrativeService.generate(findings, score_data, audit_run.get("active_supplement", "E01"))
    audit_run["narrative"] = narrative_data

    # Save mutated run back to Postgres
    repo.save_audit_run(audit_id, audit_run)

    # State Engine Check
    unreviewed = [f for f in findings if f.get("status") in ["open", "needs_review"]]
    crit_blockers = [f.get("rule_id") for f in unreviewed if f.get("severity") in ["critical", "high"]]
    audit_run["blockers"] = crit_blockers

    if len(unreviewed) == 0:
        audit_run["status"] = "completed"
        activity_log.append({
            "id": f"evt_{uuid.uuid4().hex[:6]}",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "actor": "system",
            "event_type": "status_change",
            "description": "All findings reviewed. Scope is Complete.",
            "metadata_context": {"status": "completed"}
        })
    else:
        if audit_run["status"] != "in_review":
            audit_run["status"] = "in_review"
            activity_log.append({
                "id": f"evt_{uuid.uuid4().hex[:6]}",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "actor": "system",
                "event_type": "status_change",
                "description": "Auditor began active review.",
                "metadata_context": {"status": "in_review"}
            })

    return {
       "finding": target_f,
       "scorecard": new_scorecard,
       "narrative": narrative_data,
       "summary_counts": score_data.get("finding_counts", {}),
       "status": audit_run["status"],
       "blockers": audit_run["blockers"],
       "activity_log": audit_run["activity_log"]
    }


from services.learning_service import LearningService

@audit_router.get("/claims/{claim_id}/history")
def get_historical_claim_intelligence(claim_id: str):
    res = LearningService.get_claim_history(claim_id)
    if "error" in res:
        raise HTTPException(status_code=404, detail=res["error"])
    return res


@audit_router.post("/audits/{audit_id}/findings/{finding_id}/vision")
def trigger_manual_vision(audit_id: str, finding_id: str):
    audit_run = repo.get_audit_run(audit_id)
    if not audit_run:
        raise HTTPException(status_code=404, detail="Audit run not found")

    target_f = next((f for f in audit_run.get("findings", []) if f["id"] == finding_id), None)
    if not target_f:
        raise HTTPException(status_code=404, detail="Finding not found")

    ev_refs = target_f.get("evidence_refs", [])
    img_urls = [e.get("url") for e in ev_refs if e.get("type") == "photo" and e.get("url")]

    vision_res = {
        "supports_damage": False,
        "confidence": 0.0,
        "notes": "",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "error": None
    }

    if not img_urls:
        vision_res["error"] = "No photos available to scan."
    else:
        v_payload = {
            "question": f"Please verify if the photo supports the {target_f.get('operation_type')} operation on {target_f.get('part_type')}.",
            "image_urls": img_urls[:3],
            "context": {
                "part_type": target_f.get("part_type"),
                "operation_type": target_f.get("operation_type"),
                "finding_id": finding_id
            }
        }

        from services.hermes_orchestrator import get_hermes_provider
        provider = get_hermes_provider()
        res_dict = provider.evaluate_vision(v_payload)

        if not res_dict:
            vision_res["error"] = "Vision check timed out or failed to connect."
        else:
            vision_res["supports_damage"] = res_dict.get("supports_damage", False)
            vision_res["confidence"] = res_dict.get("confidence", 0.0)
            vision_res["notes"] = res_dict.get("notes", "")

    target_f["vision_result"] = vision_res
    repo.save_audit_run(audit_id, audit_run)

    # Phase 11: Sync manual vision back into HermesLog
    from database.database import SessionLocal
    from database.models import HermesLog

    v_trig = True
    v_succ = not bool(vision_res["error"])
    v_error = vision_res["error"]
    v_timeout = v_error and ("timed out" in v_error.lower() or "fail" in v_error.lower())

    with SessionLocal() as db:
        log_entry = db.query(HermesLog).filter_by(target_id=finding_id, target_type="finding").order_by(HermesLog.id.desc()).first()
        if log_entry:
            log_entry.vision_triggered = True
            log_entry.vision_success = v_succ
            log_entry.vision_timeout = v_timeout
            log_entry.vision_error = v_error
            db.commit()

    return {"finding": target_f, "vision_result": vision_res}


# ============================================================================
# Fast QC Endpoint — instant rules engine audit, no Hermes/VPS
# ============================================================================

@audit_router.post("/qc")
async def run_qc_audit(
    request: Request,
    ems_zip: UploadFile = File(None),
    estimate_pdf: UploadFile = File(None),
):
    """
    Fast QC audit — parses uploaded file and runs rules engine only.
    No Hermes, no VPS, no background processing. Returns instant findings.
    Accepts either CCC ZIP (.lin) or estimate PDF.
    """
    request_id = getattr(request.state, "request_id", "unknown")
    set_correlation_id(request_id)

    parsed_data = None
    file_type = "unknown"

    # Try CCC ZIP first
    if ems_zip and ems_zip.filename:
        contents = await ems_zip.read()
        validate_upload_size(contents, ems_zip.filename)

        if ems_zip.filename.lower().endswith('.zip'):
            file_type = "ccc_zip"
            from parser.ems_parser import EmsParser
            parser = EmsParser()
            parsed_data = parser.analyze_zip(io.BytesIO(contents))

    # Try PDF
    if estimate_pdf and estimate_pdf.filename and not parsed_data:
        contents = await estimate_pdf.read()
        validate_upload_size(contents, estimate_pdf.filename)

        if estimate_pdf.filename.lower().endswith('.pdf'):
            file_type = "pdf"
            try:
                from parser.pdf_estimate_parser import PDFEstimateParser
                parser = PDFEstimateParser()
                parsed_data = parser.parse_pdf(io.BytesIO(contents))
            except Exception as e:
                logger.warning(f"PDF parse failed: {e}")

    if not parsed_data:
        raise HTTPException(status_code=400, detail="No valid estimate file found. Upload a CCC ZIP or estimate PDF.")

    # Run rules engine
    from rules_engine import RulesEngine
    engine = RulesEngine()
    result = engine.evaluate_estimate(parsed_data)

    findings = (
        result.get("audit", {}).get("base_findings", []) +
        result.get("audit", {}).get("carrier_overlays", {}).get("natgen", {}).get("findings", [])
    )

    # Detect supplement
    is_supplement = any(
        str(r.get("supplement", "")).upper() not in ("", "E01")
        for p in parsed_data.get("claim", {}).get("panels", [])
        for r in p.get("rows", [])
    )

    # Use shared audit presentation utility
    from services.audit_presentation import group_findings, build_passed, CONFIDENCE

    groups = group_findings(findings)

    meta = parsed_data.get("claim_meta", {})
    vehicle = meta.get("vehicle", {})
    shop = meta.get("shop", {})

    passed = build_passed(parsed_data, shop, is_supplement)

    finding_result = {
        "audit_id": f"qc_{uuid.uuid4().hex[:8]}",
        "file_type": file_type,
        "is_supplement": is_supplement,
        "claim_number": meta.get("claim_number", "?"),
        "vehicle": {
            "year": vehicle.get("year"),
            "make": vehicle.get("make"),
            "model": vehicle.get("model"),
            "mileage": vehicle.get("mileage"),
            "vin": vehicle.get("vin"),
        },
        "shop": {
            "name": shop.get("name", ""),
            "state": shop.get("state", ""),
            "address": shop.get("address", ""),
            "phone": shop.get("phone", ""),
        },
        "findings": {
            "state": [{"severity": f.get("severity"), "summary": f.get("summary"), "lines": f.get("affected_lines", []), "confidence": CONFIDENCE.get(f.get("rule_id",""), 0.7)} for f in groups.get("state", [])],
            "remove": [{"severity": f.get("severity"), "summary": f.get("summary"), "lines": f.get("affected_lines", []), "confidence": CONFIDENCE.get(f.get("rule_id",""), 0.7)} for f in groups.get("remove", [])],
            "fix": [{"severity": f.get("severity"), "summary": f.get("summary"), "lines": f.get("affected_lines", []), "confidence": CONFIDENCE.get(f.get("rule_id",""), 0.7)} for f in groups.get("fix", [])],
            "verify": [{"severity": f.get("severity"), "summary": f.get("summary"), "lines": f.get("affected_lines", []), "confidence": CONFIDENCE.get(f.get("rule_id",""), 0.7)} for f in groups.get("verify", [])],
            "attach": [{"severity": f.get("severity"), "summary": f.get("summary"), "lines": f.get("affected_lines", []), "confidence": CONFIDENCE.get(f.get("rule_id",""), 0.7)} for f in groups.get("attach", [])],
            "review": [{"severity": f.get("severity"), "summary": f.get("summary"), "lines": f.get("affected_lines", []), "confidence": CONFIDENCE.get(f.get("rule_id",""), 0.7)} for f in groups.get("review", [])],
        },
        "total_findings": len(findings),
        "passed": passed,
        "_analytics": {
            "rule_ids": list(set(f.get("rule_id") for f in findings)),
            "by_severity": {
                sev: len([f for f in findings if f.get("severity") == sev])
                for sev in ["critical", "high", "medium", "low"]
            },
            "by_category": {
                cat: len(items)
                for cat, items in groups.items() if items
            }
        }
    }

    # Track to database for persistent analytics
    from analytics import track_audit_findings
    track_audit_findings(findings, meta.get("claim_number", ""), file_type)

    return finding_result


@audit_router.get("/analytics")
def get_analytics():
    """Return aggregate analytics for all tracked audits."""
    from analytics import get_analytics
    return get_analytics()


# ============================================================================
# Vision Analysis Endpoint
# ============================================================================

@audit_router.post("/vision")
async def analyze_photos(
    request: Request,
    photos: List[UploadFile] = File(...),
):
    """
    Analyze uploaded damage photos using qwen3-vl:235b.
    Returns per-photo damage assessment with panel, damage type, and confidence.
    """
    request_id = getattr(request.state, "request_id", "unknown")
    set_correlation_id(request_id)

    if not photos:
        raise HTTPException(status_code=400, detail="No photos uploaded.")

    results = []

    for photo in photos[:10]:  # Max 10 photos per request
        contents = await photo.read()
        if len(contents) == 0:
            continue

        img_b64 = _b64.b64encode(contents).decode()
        data_url = f"data:image/jpeg;base64,{img_b64}"

        # Call vision model
        payload = {
            "model": "qwen3-vl:235b",
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "text", "text": (
                        "You are an automotive damage appraiser. Examine this photo and respond with JSON only:\n"
                        '{"panel": "string", "damage_present": bool, "damage_description": "string", '
                        '"damage_type": "dent|scratch|crack|tear|missing|none", '
                        '"recommended_operation": "Replace|Repair|None", '
                        '"confidence": 0.0-1.0, "notes": "string"}'
                    )},
                    {"type": "image_url", "image_url": {"url": data_url}}
                ]
            }],
            "temperature": 0.2, "max_tokens": 300,
        }

        try:
            import urllib.request
            api_key = os.environ.get("OLLAMA_CLOUD_API_KEY", "")
            if not api_key:
                results.append({"filename": photo.filename, "error": "Vision API key not configured"})
                continue

            url = "https://ollama.com/v1/chat/completions"
            data = _json.dumps(payload).encode()
            headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}

            req = urllib.request.Request(url, data=data, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=60) as resp:
                result = _json.loads(resp.read())

            content = result["choices"][0]["message"]["content"]
            parsed = _json.loads(content)
            parsed["filename"] = photo.filename
            results.append(parsed)

        except Exception as e:
            logger.error(f"Vision call failed for {photo.filename}: {e}")
            results.append({"filename": photo.filename, "error": str(e)[:200]})

    return {"photos_analyzed": len(results), "results": results}
