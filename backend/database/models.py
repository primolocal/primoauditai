from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime, UniqueConstraint, JSON, Float, Enum as SQLEnum
from datetime import datetime
from schemas import LogicReasonEnum, ActionReasonEnum, TruthStatusEnum, LearningCandidateType
from database.database import Base

class LearningCandidate(Base):
    __tablename__ = "learning_candidates"
    id = Column(Integer, primary_key=True)
    candidate_fingerprint = Column(String, unique=True, index=True, nullable=False)
    type = Column(SQLEnum(LearningCandidateType), nullable=False)
    rule_id = Column(String, nullable=True)
    description = Column(Text, nullable=False)
    evidence_json = Column(JSON, nullable=True)
    confidence_score = Column(Float, nullable=True)
    status = Column(String, default="pending", nullable=False)
    implementation_status = Column(String, default="queued", nullable=False)
    admin_note = Column(Text, nullable=True)
    git_commit_hash = Column(String, nullable=True)
    change_type = Column(String, nullable=True)
    rule_version = Column(String, nullable=True)
    prompt_version = Column(String, nullable=True)
    deployed_at = Column(DateTime, nullable=True)
    implemented_by = Column(String, nullable=True)
    effectiveness_status = Column(String, default="pending_evaluation", nullable=False)
    impact_summary_json = Column(JSON, nullable=True)
    
    # Phase 17: Closed-Loop Optimization Engine
    priority_score = Column(Float, default=0.0)
    source = Column(String, nullable=True)
    affected_carriers = Column(JSON, nullable=True)
    affected_rules = Column(JSON, nullable=True)
    sample_size = Column(Integer, default=0)
    example_evidence_json = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    reviewed_at = Column(DateTime, nullable=True)
    reviewed_by = Column(String, nullable=True)

class ProcessingJob(Base):
    __tablename__ = "processing_jobs"
    id = Column(Integer, primary_key=True)
    job_id = Column(String, unique=True, index=True, nullable=False)
    audit_id = Column(String, index=True, nullable=True) # Mapped once created
    status = Column(String, default="processing", nullable=False)
    progress_percentage = Column(Integer, default=0)
    message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

class AssetRecordModel(Base):
    __tablename__ = "asset_records"
    id = Column(Integer, primary_key=True)
    audit_id = Column(String, index=True, nullable=False)
    asset_id = Column(String, unique=True, index=True, nullable=False)
    role = Column(String, nullable=True)
    storage_key = Column(String, nullable=False)
    original_filename = Column(String, nullable=False)
    content_type = Column(String, nullable=True)
    byte_size = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

class AuditRun(Base):
    __tablename__ = "audit_runs"
    id = Column(Integer, primary_key=True)
    audit_id = Column(String, unique=True, index=True, nullable=False)
    claim_id = Column(String, nullable=True)
    auditor_id = Column(String, nullable=True) # Phase 20 Auditor tracking
    claim_readiness = Column(String, nullable=True)
    summary_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

class ClaimRecord(Base):
    __tablename__ = "claim_records"
    id = Column(Integer, primary_key=True)
    claim_number = Column(String, unique=True, index=True, nullable=False)
    carrier = Column(String, nullable=True)
    loss_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

class ClaimAuditRecord(Base):
    __tablename__ = "claim_audit_records"
    id = Column(Integer, primary_key=True)
    claim_number = Column(String, index=True, nullable=False)
    audit_id = Column(String, unique=True, index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

class FindingReview(Base):
    __tablename__ = "finding_reviews"
    id = Column(Integer, primary_key=True)
    audit_id = Column(String, index=True, nullable=False)
    finding_id = Column(String, index=True, nullable=False)
    health_status = Column(String, nullable=True)
    health_explanation = Column(Text, nullable=True)
    is_unresolved_override = Column(Boolean, default=False, nullable=False)
    reviewer_note = Column(Text, nullable=True)
    evidence_exists = Column(String, nullable=True)
    evidence_uploaded = Column(String, nullable=True)
    linked_asset_ids = Column(Text, nullable=True)
    missing_upload_reason = Column(String, nullable=True)
    
    # Hermes & Supervisor Tracking
    hermes_critique = Column(Text, nullable=True)
    auditor_outcome = Column(String, nullable=True)
    auditor_reason_code = Column(SQLEnum(LogicReasonEnum), nullable=True)
    guideline_citation = Column(String, nullable=True)

    # Phase 6: Recommendation Feedback Tracking
    suggested_action_type = Column(String, nullable=True)
    suggested_revision = Column(JSON, nullable=True)
    requires_manual_confirmation = Column(Boolean, nullable=True)
    supporting_reason = Column(Text, nullable=True)
    recommendation_outcome = Column(String, nullable=True)
    recommendation_reason_code = Column(SQLEnum(ActionReasonEnum), nullable=True)
    
    # Phase 7: Enum Normalization & Truth Validation Tracking
    finding_reason_comment = Column(Text, nullable=True)
    recommendation_reason_comment = Column(Text, nullable=True)
    finding_truth_status = Column(SQLEnum(TruthStatusEnum), nullable=True)
    recommendation_truth_status = Column(SQLEnum(TruthStatusEnum), nullable=True)
    validation_source = Column(String, nullable=True)
    
    # Phase 13: Auditor Priority Queue
    triage_bucket = Column(String, nullable=True)
    
    # Phase 20: Coaching Analytics
    auditor_id = Column(String, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("audit_id", "finding_id", name="uq_finding_review"),
    )

class CarrierGuideline(Base):
    __tablename__ = "carrier_guidelines"
    id = Column(Integer, primary_key=True)
    carrier = Column(String, index=True, nullable=False)
    version_label = Column(String, nullable=False)
    file_url = Column(String, nullable=True)
    extracted_text = Column(Text, nullable=True)
    checksum = Column(String, nullable=True)
    status = Column(String, default="pending_review", nullable=False)
    hermes_analysis = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

class AssetVerdict(Base):
    __tablename__ = "asset_verdicts"
    id = Column(Integer, primary_key=True)
    audit_id = Column(String, index=True, nullable=False)
    finding_id = Column(String, index=True, nullable=False)
    asset_id = Column(String, index=True, nullable=False)
    system_support_quality = Column(String, nullable=True)
    auditor_verdict = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("audit_id", "finding_id", "asset_id", name="uq_asset_verdict"),
    )

class HermesLog(Base):
    __tablename__ = "hermes_logs"
    id = Column(Integer, primary_key=True)
    input_hash = Column(String, index=True, nullable=True)
    target_id = Column(String, index=True, nullable=False) # ClaimID, AuditID, or FindingID
    target_type = Column(String, nullable=False) # "finding" or "claim"
    generated_text = Column(Text, nullable=True)
    banner_text = Column(Text, nullable=True)
    advisory_tone = Column(String, nullable=True)
    escalation_hint = Column(String, nullable=True)
    
    # Phase 10: Measurable Hermes Tuning
    hermes_version = Column(String, nullable=True)
    template_family = Column(String, nullable=True)
    wording_variant = Column(String, nullable=True)
    strength_label = Column(String, nullable=True)
    primary_reason_code = Column(String, nullable=True)
    reason_codes_json = Column(JSON, nullable=True)
    carrier = Column(String, nullable=True)
    rule_id = Column(String, nullable=True)
    
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    provider = Column(String, nullable=True)
    reviewer_outcome = Column(String, nullable=True)
    truth_outcome = Column(String, nullable=True)
    
    # Phase 8 & 8.5: Vision Telemetry
    vision_triggered = Column(Boolean, default=False)
    vision_success = Column(Boolean, default=False)
    vision_timeout = Column(Boolean, default=False)
    vision_error = Column(String, nullable=True)
    
    # Phase 13: Auditor Priority Queue
    triage_bucket = Column(String, nullable=True)

    # Phase 16: Playbook Outcomes
    primary_action = Column(String, nullable=True)


class AnalyticsLog(Base):
    """Tracks finding counts per rule for aggregate analytics."""
    __tablename__ = "analytics_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    rule_id = Column(String, nullable=False)
    severity = Column(String, nullable=False)
    category = Column(String, nullable=False)
    claim_number = Column(String, nullable=True)
    file_type = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
