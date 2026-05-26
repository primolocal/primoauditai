from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from services.learning_service import LearningService
from services.coaching_service import CoachingService
from pydantic import BaseModel
from typing import List, Optional, Literal

router = APIRouter(prefix="/api/learning", tags=["Learning System"])

class TruthAttachmentLine(BaseModel):
    line_id: Optional[str] = None
    part_type: Optional[str] = None
    operation_type: Optional[str] = None
    description: Optional[str] = None
    final_carrier_status: str

class TruthAttachmentPayload(BaseModel):
    event_type: str
    source: str
    timestamp: str
    lines: List[TruthAttachmentLine]

@router.get("/metrics")
async def get_metrics(test_mode: bool = False):
    try:
        data = LearningService.synthesize_metrics(test_mode=test_mode)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/hermes-metrics")
async def get_hermes_metrics():
    try:
        return LearningService.synthesize_hermes_effectiveness()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/attach-truth/{claim_id}")
async def attach_truth_preview(claim_id: str, payload: TruthAttachmentPayload):
    try:
        preview = LearningService.evaluate_truth_preview(claim_id, payload.lines)
        return preview
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class CandidateReviewPayload(BaseModel):
    status: Literal["approved", "rejected"]
    admin_note: Optional[str] = None
    admin_name: str = "system_admin"

class CandidateImplementationPayload(BaseModel):
    implementation_status: Literal["queued", "in_progress", "implemented", "declined"]
    git_commit_hash: Optional[str] = None
    change_type: Optional[str] = None
    rule_version: Optional[str] = None
    prompt_version: Optional[str] = None
    deployed_at: Optional[str] = None
    implemented_by: Optional[str] = None

@router.post("/generate-candidates")
async def trigger_candidates_generation(min_n: int = 10):
    try:
        return LearningService.generate_learning_candidates(min_n=min_n)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/candidates")
async def fetch_candidates(status: Optional[str] = "all"):
    try:
        return {"candidates": LearningService.get_candidates(status_filter=status)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/candidates/{candidate_id}/review")
async def submit_candidate_review(candidate_id: int, payload: CandidateReviewPayload):
    try:
        res = LearningService.review_candidate(candidate_id, payload.status, payload.admin_name, payload.admin_note)
        if "error" in res:
            raise HTTPException(status_code=404, detail=res["error"])
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/candidates/{candidate_id}/implementation")
async def update_candidate_implementation(candidate_id: int, payload: CandidateImplementationPayload):
    try:
        res = LearningService.update_candidate_implementation(
            candidate_id, 
            payload.implementation_status,
            payload.git_commit_hash,
            payload.change_type,
            payload.rule_version,
            payload.prompt_version,
            payload.deployed_at,
            payload.implemented_by
        )
        if "error" in res:
            raise HTTPException(status_code=404, detail=res["error"])
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/candidates/{candidate_id}/evaluate-impact")
async def trigger_candidate_impact_evaluation(candidate_id: int):
    try:
        res = LearningService.evaluate_candidate_impact(candidate_id)
        if "error" in res:
            raise HTTPException(status_code=400, detail=res["error"])
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/evaluate-candidate-impact/{candidate_id}")
def force_evaluate_candidate(candidate_id: int):
    result = LearningService.evaluate_candidate_impact(int(candidate_id), override_limit=False)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@router.get("/coaching/auditors", status_code=200)
def list_auditors():
    try:
        return {"auditors": CoachingService.get_auditors()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/coaching/auditor/{auditor_id}", status_code=200)
def get_auditor_coaching(auditor_id: str):
    try:
        return CoachingService.synthesize_auditor_coaching(auditor_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
