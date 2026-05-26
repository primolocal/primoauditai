from typing import List, Optional, Dict, Literal
from pydantic import BaseModel, Field, model_validator
from enum import Enum

class LogicReasonEnum(str, Enum):
    INVALID_GUIDELINE = "INVALID_GUIDELINE"
    MISSING_CONTEXT = "MISSING_CONTEXT"
    INCORRECT_OPERATION = "INCORRECT_OPERATION"
    BUSINESS_EXCEPT = "BUSINESS_EXCEPT"
    DUPLICATE = "DUPLICATE"
    INCOMPLETE_SCOPE = "INCOMPLETE_SCOPE"
    CARRIER_EXCEPTION = "CARRIER_EXCEPTION"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    OTHER = "OTHER"

class ActionReasonEnum(str, Enum):
    PENALTY_TOO_HIGH = "PENALTY_TOO_HIGH"
    PENALTY_TOO_LOW = "PENALTY_TOO_LOW"
    WRONG_ACTION_TYPE = "WRONG_ACTION_TYPE"
    NOT_ACTIONABLE = "NOT_ACTIONABLE"
    OTHER = "OTHER"

class TruthStatusEnum(str, Enum):
    VALIDATED = "VALIDATED"
    PARTIAL_VALIDATION = "PARTIAL_VALIDATION"
    OVERTURNED = "OVERTURNED"
    TOO_AGGRESSIVE = "TOO_AGGRESSIVE"
    MISSED_PREVIOUSLY = "MISSED_PREVIOUSLY"
    UNRESOLVED = "UNRESOLVED"

class LearningCandidateType(str, Enum):
    RULE_ADJUSTMENT = "RULE_ADJUSTMENT"
    WORDING_ADJUSTMENT = "WORDING_ADJUSTMENT"
    RECOMMENDATION_TUNING = "RECOMMENDATION_TUNING"
    MISSED_PATTERN_ALERT = "MISSED_PATTERN_ALERT"
    CARRIER_SPECIFIC_BEHAVIOR = "CARRIER_SPECIFIC_BEHAVIOR"
    TRIAGE_TUNING = "TRIAGE_TUNING"
    PLAYBOOK_TUNING = "PLAYBOOK_TUNING"

# 1. File Inventory
class FileInfo(BaseModel):
    filename: str
    file_type: str
    size_bytes: int

class FileInventory(BaseModel):
    files: List[FileInfo] = Field(default_factory=list)
    total_files: int = 0
    parse_errors: List[str] = Field(default_factory=list)

# 1.5. Asset Registry
class AssetRecord(BaseModel):
    asset_id: str
    storage_key: str
    original_filename: str
    content_type: str
    asset_type: Literal['image', 'pdf', 'other']
    doc_type: str
    processing_status: Literal['uploaded', 'stored', 'preview_ready', 'classified', 'cv_pending', 'cv_complete', 'mapped', 'failed'] = 'uploaded'
    source_kind: Literal['uploaded', 'extracted_from_zip', 'generated_fixture'] = 'extracted_from_zip'
    parent_asset_id: Optional[str] = None
    ingested_at: Optional[str] = None
    extraction_method: Optional[str] = None
    reason: Optional[str] = None
    is_mock: bool = False
    url: str
    thumbnail_url: Optional[str] = None

# 2. Vehicle Profile
class VehicleProfile(BaseModel):
    year: Optional[int] = None
    make: Optional[str] = None
    model: Optional[str] = None
    vin: Optional[str] = None
    mileage: Optional[int] = None
    acv: Optional[float] = None
    impact_primary: Optional[str] = None

# 3. Shop Profile
class ShopProfile(BaseModel):
    name: Optional[str] = None
    tax_id: Optional[str] = None
    phone: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    drp_status: bool = False

# 4. Estimate Lines
class EstimateLine(BaseModel):
    line_no: int
    operation: str
    description: str
    operation_type: Optional[str] = None
    operation_code: Optional[str] = None
    part_type: Optional[str] = None
    part_number: Optional[str] = None
    quantity: float = 1.0
    price: float = 0.0
    labor_hours: float = 0.0
    paint_hours: float = 0.0
    sublet_amount: float = 0.0
    raw_data: Optional[Dict] = None
    delta_status: Literal['added', 'modified', 'removed', 'unchanged', 'original'] = 'original'

class EstimateTotal(BaseModel):
    gross_total: float = 0.0
    net_total: float = 0.0
    total_labor: float = 0.0
    total_labor_hours: float = 0.0
    total_parts: float = 0.0
    total_paint: float = 0.0

class EstimateLines(BaseModel):
    items: List[EstimateLine] = Field(default_factory=list)
    totals: EstimateTotal = Field(default_factory=EstimateTotal)
    supplement_count: int = 0

# 5. Claim Package
class ClaimPackage(BaseModel):
    claim_number: str
    carrier: str
    status: str = "New"
    loss_date: Optional[str] = None
    deductible: Optional[float] = None

# 6. Evidence Matrix
class NormalizedDocument(BaseModel):
    id: str
    filename: str
    doc_type: str
    extracted_text: Optional[str] = None
    source_url: str
    thumbnail_url: Optional[str] = None
    processing_status: Literal['not started', 'processing', 'complete', 'failed'] = 'complete'
    is_mock: bool = False

class PhotoEvidence(BaseModel):
    id: str
    url: str
    thumbnail_url: Optional[str] = None
    type: str # exterior, interior, vin, doc
    damage_area: Optional[str] = None
    clarity: str = "unknown"
    confidence: Optional[float] = None

class EvidenceMatrix(BaseModel):
    processing_status: Literal['not started', 'processing', 'complete', 'partial', 'failed'] = 'complete'
    documents: List[NormalizedDocument] = Field(default_factory=list)
    photos: List[PhotoEvidence] = Field(default_factory=list)
    missing_required_photos: List[str] = Field(default_factory=list)
    photo_sufficiency_score: float = 0.0

# 6.5 Evidence Reference
class EvidenceRef(BaseModel):
    id: str
    type: Literal['scan_pdf', 'supplement_doc', 'photo', 'invoice', 'missing']
    source_id: Optional[str] = None
    label: str
    support_status: Literal['full', 'partial', 'missing']
    reason: str
    page_or_image: Optional[str] = None
    url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    confidence: Optional[float] = None
    linked_tags: List[str] = Field(default_factory=list)
    is_mock: bool = False
# 6.6 Historical Intelligence Model
class HistoricalSignal(BaseModel):
    type: str # historically_overturned, recommendation_risk, carrier_historically_validated
    source: Literal['claim', 'carrier', 'finding']
    weight: float
    reason: str
    match_confidence: float
    # Phase 7.5 Temporal Dynamics
    event_age_days: int = 0
    recency_multiplier: float = 1.0
    match_count: int = 0
    validated_count: int = 0
    overturned_count: int = 0
    recommendation_reject_count: int = 0
    effective_weight: float = 1.0

# Phase 8: Hermes Vision
class HermesVisionContext(BaseModel):
    part_type: Optional[str] = None
    operation_type: Optional[str] = None
    finding_id: str

class HermesVisionRequest(BaseModel):
    question: str
    image_urls: List[str]
    context: HermesVisionContext

class HermesVisionResponse(BaseModel):
    supports_damage: bool
    confidence: float
    notes: str
    timestamp: Optional[str] = None
    error: Optional[str] = None

# Phase 15: Action Playbook
class ActionPlaybook(BaseModel):
    primary_action: str
    steps: List[str] = Field(default_factory=list)
    escalate_if: List[str] = Field(default_factory=list)
    do_not_do: List[str] = Field(default_factory=list)

# 7. Finding
class Finding(BaseModel):
    id: str
    rule_id: str
    severity: Literal['high', 'medium', 'low']
    category: str
    message: str
    affected_lines: List[int] = Field(default_factory=list)
    evidence_refs: List[EvidenceRef] = Field(default_factory=list)
    recommended_action: str
    status: Literal['open', 'confirmed', 'overturned', 'needs_review', 'deferred'] = 'open'
    financial_impact: float = 0.0
    confidence: float = 1.0
    is_supplement_issue: bool = False
    # Phase 6.5 & 7
    historical_signals: Optional[List[HistoricalSignal]] = Field(default_factory=list)
    
    # Phase 8: Vision
    vision_result: Optional[HermesVisionResponse] = None
    
    # Hermes & Auditor additions
    hermes_critique: Optional[str] = None
    guideline_citation: Optional[str] = None
    auditor_outcome: Optional[Literal['confirm', 'edit', 'dismiss']] = None
    auditor_reason_code: Optional[str] = None
    auditor_comment: Optional[str] = None
    hermes_recommended_action: Optional[Literal['approve', 'dismiss', 'review']] = None
    hermes_confidence_level: Optional[Literal['high', 'medium', 'low']] = None
    hermes_short_reason: Optional[str] = None
    pattern_detection_flags: List[str] = Field(default_factory=list)
    pattern_related_lines: List[int] = Field(default_factory=list)
    
    # Phase 5: Recommendation Fields
    suggested_action_type: Optional[str] = None
    suggested_revision: Optional[dict] = None
    requires_manual_confirmation: bool = True
    supporting_reason: Optional[str] = None
    
    # Phase 6: Recommendation Feedback Fields
    recommendation_outcome: Optional[Literal['accepted', 'modified', 'rejected']] = None
    recommendation_reason_code: Optional[str] = None
    
    # Phase 7: Operation Context & Debugging
    debug_context: Optional[dict] = None

    # Phase 13: Priority Queue
    triage_priority_score: float = 0.0
    triage_bucket: Literal['Address First', 'Needs Review', 'Request Support', 'Low Urgency'] = 'Low Urgency'

    # Phase 15: Resolution Playbooks
    action_playbook: Optional[ActionPlaybook] = None

# 8. Rule Result
class RuleResult(BaseModel):
    rule_id: str
    passed: bool
    points_deducted: int = 0
    rationale: str

# 9. Scorecard
class CategoryScores(BaseModel):
    structural_integrity: int = 100
    line_item_support: int = 100
    parts_accuracy: int = 100
    labor_reasonableness: int = 100
    documentation_readiness: int = 100
    carrier_compliance: int = 100

class Scorecard(BaseModel):
    overall_score: int = 100
    verdict: Literal['Pass', 'Review', 'Fail'] = 'Pass'
    category_scores: CategoryScores = Field(default_factory=CategoryScores)
    confidence: float = 1.0

# 10. Narrative Block
class NarrativeBlock(BaseModel):
    damage_summary: str = ""
    claim_summary: str = ""
    reviewer_notes: str = ""
    escalation_note: str = ""

# 11. Reviewer Feedback
class ReviewerAction(BaseModel):
    finding_id: str
    action: Literal['confirm', 'override', 'defer']
    reason_code: Optional[str] = None
    comment: Optional[str] = None
    timestamp: Optional[str] = None

class ReviewerFeedback(BaseModel):
    actions: List[ReviewerAction] = Field(default_factory=list)
    audit_duration_seconds: int = 0
    final_verdict: Optional[str] = None

# 11.5 Activity Log
class ActivityEvent(BaseModel):
    id: str
    timestamp: str
    actor: Literal['system', 'auditor']
    event_type: str
    description: str
    metadata_context: Optional[dict] = None

# 11.6 Hermes Tasks
class HermesTask(BaseModel):
    id: str
    finding_id: str
    line_number: int
    label: str
    severity: str
    score_impact: int
    status: Literal['pending', 'resolved'] = 'pending'
    allowed_actions: List[str] = Field(default_factory=list)

class HermesTaskQueue(BaseModel):
    tasks: List[HermesTask] = Field(default_factory=list)
    total_tasks: int = 0
    resolved_tasks: int = 0

class HermesRunMetadata(BaseModel):
    hermes_run_id: str
    hermes_status: str
    hermes_started_at: str
    hermes_completed_at: Optional[str] = None
    hermes_elapsed_ms: Optional[int] = None
    hermes_error_code: Optional[str] = None
    hermes_error_message: Optional[str] = None

# 12. Audit Run
class AuditRun(BaseModel):
    run_id: str
    timestamp: str
    status: Literal['not_started', 'in_review', 'needs_follow_up', 'escalated', 'completed'] = 'not_started'
    ingestion_status: Literal['pending', 'processing', 'normalized', 'failed'] = 'pending'
    hermes_status: Literal['pending', 'processing', 'success', 'failed', 'skipped'] = 'pending'
    hermes_run_metadata: Optional[HermesRunMetadata] = None
    manual_review_mode: bool = False
    active_supplement: str = "E01"
    
    # State tracking
    previous_runs: List[str] = Field(default_factory=list)
    blockers: List[str] = Field(default_factory=list)
    activity_log: List[ActivityEvent] = Field(default_factory=list)
    
    # Core Data
    claim_package: ClaimPackage
    file_inventory: FileInventory
    vehicle_profile: VehicleProfile
    shop_profile: ShopProfile
    estimate_lines: EstimateLines
    evidence_matrix: EvidenceMatrix
    
    # Output Data
    findings: List[Finding] = Field(default_factory=list)
    rule_results: List[RuleResult] = Field(default_factory=list)
    scorecard: Scorecard = Field(default_factory=Scorecard)
    narrative: NarrativeBlock = Field(default_factory=NarrativeBlock)
    reviewer_feedback: ReviewerFeedback = Field(default_factory=ReviewerFeedback)
    hermes_tasks: Optional[HermesTaskQueue] = None

# 13. Hermes Context Boundaries
class HermesFindingResponse(BaseModel):
    final_recommendation_text: str
    advisory_tone: str
    escalation_hint: str
    hermes_rationale_summary: str
    template_family: str
    wording_variant: str
    strength_label: str
    primary_reason_code: str
    supporting_reason_codes: Optional[List[str]] = Field(default_factory=list)
    action_playbook: Optional[ActionPlaybook] = None
    
    # New Decision Support Fields
    recommended_action: Literal['approve', 'dismiss', 'review'] = 'review'
    confidence_level: Literal['high', 'medium', 'low'] = 'medium'
    short_reason: str = "Pending Context"
    pattern_detection_flags: List[str] = Field(default_factory=list)
    pattern_related_lines: List[int] = Field(default_factory=list)

class HermesTriageItem(BaseModel):
    finding_id: str
    title: str
    short_reason: str

class HermesClaimLevelBanner(BaseModel):
    type: Literal['warning', 'secondary', 'info', 'error'] = 'info'
    title: str
    message: str

class HermesResponsePayload(BaseModel):
    findings: Dict[str, HermesFindingResponse] = Field(default_factory=dict)
    advisory_banners: List[HermesClaimLevelBanner] = Field(default_factory=list)
    top_triage_items: List[HermesTriageItem] = Field(default_factory=list)

# --- API Payload Models (moved from api/main.py) ---

class ActionPayload(BaseModel):
    reason_code: Optional[LogicReasonEnum] = None
    comment: Optional[str] = None
    recommendation_outcome: Optional[str] = None
    recommendation_reason: Optional[ActionReasonEnum] = None
    recommendation_comment: Optional[str] = None

    @model_validator(mode="after")
    def validate_other_requires_comment(self):
        if self.reason_code == LogicReasonEnum.OTHER and not self.comment:
            raise ValueError("Comment is required when 'OTHER' rule rejection reason is selected.")
        if self.recommendation_reason == ActionReasonEnum.OTHER and not self.recommendation_comment:
            raise ValueError("Comment is required when 'OTHER' action rejection reason is selected.")
        return self


class FindingReviewPayload(BaseModel):
    finding_id: str
    note: Optional[str] = None
    health_status: Optional[str] = None
    health_explanation: Optional[str] = None
    evidence_exists: Optional[str] = None
    evidence_uploaded: Optional[str] = None
    linked_asset_ids: Optional[List[str]] = None
    missing_upload_reason: Optional[str] = None
    hermes_critique: Optional[str] = None
    auditor_outcome: Optional[str] = None
    auditor_reason_code: Optional[str] = None
    guideline_citation: Optional[str] = None


class AssetVerdictPayload(BaseModel):
    state_key: str
    verdict: Optional[str] = None


class ActivityEventPayload(BaseModel):
    event_type: str
    description: str
    metadata_context: Optional[dict] = None
    vision_result: Optional[dict] = None


class HermesAdvisoryPayload(BaseModel):
    audit_id: str
    carrier: str
    claim_meta: dict
    findings: list
    category_scores: dict
    historical_patterns: dict
    auditor_context: dict
