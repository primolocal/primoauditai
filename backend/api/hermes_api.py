from fastapi import APIRouter, BackgroundTasks
from schemas_hermes import HermesAuditRequest, HermesAuditResponse, HermesFeedbackRequest, HermesFeedbackResponse

router = APIRouter()

@router.post("/hermes/audit", response_model=HermesAuditResponse)
async def run_hermes_audit(request: HermesAuditRequest):
    """
    Hermes Intelligence Engine API.
    Absorbs normalized claim data, evaluates rules, generates findings, and prioritizes a task queue.
    """
    
    # 1. Run local rules engine (acting as the brain of Hermes for this module)
    from rules_engine import RulesEngine
    engine = RulesEngine()
    
    # Assemble parsed_data for RulesEngine
    parsed_data = {
        "claim_package": request.claim_package,
        "vehicle_profile": request.vehicle_profile,
        "shop_profile": request.shop_profile,
        "estimate_lines": request.estimate_lines,
        "evidence_matrix": request.evidence_matrix
    }
    
    evaluated_data = engine.evaluate_estimate(parsed_data)
    
    # 2. Build finding structure
    from adapter import build_audit_run
    strict_result = build_audit_run(evaluated_data, audit_id=request.audit_id)
    
    # 3. Apply Hermes Orchestration & Task Sequencing
    from services.hermes_orchestrator import finalize_audit_advisory
    finalize_audit_advisory(strict_result, strict_result.get("findings", []))
    
    # 4. Return Intelligence Payload
    return HermesAuditResponse(
        tasks=strict_result.get("hermes_tasks", {}),
        findings=strict_result.get("findings", []),
        rule_results=strict_result.get("rule_results", []),
        scorecard=strict_result.get("scorecard", {}),
        narrative=strict_result.get("narrative", {}),
        hermes_advisory=strict_result.get("hermes_advisory", {})
    )

@router.post("/hermes/feedback", response_model=HermesFeedbackResponse)
async def hermes_feedback(request: HermesFeedbackRequest, background_tasks: BackgroundTasks):
    """
    Hermes feedback collection API.
    Used for submitting per-finding actions (approve, dismiss, override) directly to Hermes
    for learning, without triggering a full re-audit cycle.
    """
    
    def log_feedback_to_db(audit_id, finding_id, rule_id, action, context):
        import hashlib
        from database.database import SessionLocal
        from database.models import HermesLog
        
        with SessionLocal() as db:
            log_entry = db.query(HermesLog).filter_by(
                target_id=finding_id, 
                target_type="finding"
            ).order_by(HermesLog.id.desc()).first()
            
            if log_entry:
                if action == "approve" or action == "confirm":
                    log_entry.reviewer_outcome = "confirm"
                elif action in ["dismiss", "overturn", "override"]:
                    log_entry.reviewer_outcome = "dismiss"
                
                # Also inject training signals into feedback payload
                # Could log a new HermesLog event explicitly for training
                db.commit()
                
    background_tasks.add_task(
        log_feedback_to_db, 
        request.audit_id, 
        request.finding_id, 
        request.rule_id, 
        request.action, 
        request.context
    )
    
    return HermesFeedbackResponse(
        status="success",
        message=f"Feedback for {request.finding_id} securely mapped to learning pipeline."
    )
