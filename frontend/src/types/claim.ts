// --- Wave 1 Core Architected Data Contracts ---
// These 12 objects form the primary deterministic spine of PrimoAuditAI

// 1. File Inventory
export interface FileInfo {
    filename: string;
    file_type: string;
    size_bytes: number;
}
export interface FileInventory {
    files: FileInfo[];
    total_files: number;
    parse_errors: string[];
}

// 2. Vehicle Profile
export interface VehicleProfile {
    year?: number | null;
    make?: string | null;
    model?: string | null;
    vin?: string | null;
    mileage?: number | null;
    acv?: number | null;
    impact_primary?: string | null;
}

// 3. Shop Profile
export interface ShopProfile {
    name?: string | null;
    tax_id?: string | null;
    phone?: string | null;
    city?: string | null;
    state?: string | null;
    drp_status: boolean;
}

// 4. Estimate Lines
export interface EstimateLine {
    line_no: number;
    operation: string;
    description: string;
    part_type?: string | null;
    part_number?: string | null;
    quantity: number;
    price: number;
    labor_hours: number;
    paint_hours: number;
    sublet_amount: number;
    raw_data?: Record<string, any> | null;
    delta_status?: 'added' | 'modified' | 'removed' | 'unchanged' | 'original';
}

export interface EstimateTotal {
    gross_total: number;
    net_total: number;
    total_labor: number;
    total_parts: number;
    total_paint: number;
}

export interface EstimateLines {
    items: EstimateLine[];
    totals: EstimateTotal;
    supplement_count: number;
}

// 5. Claim Package
export interface ClaimPackage {
    claim_number: string;
    carrier: string;
    status: string; // 'New', 'In Review', 'Completed'
    loss_date?: string | null;
    deductible?: number | null;
}

// 6. Evidence Matrix
export type PhotoType = 'exterior' | 'interior' | 'vin' | 'doc' | 'unknown';
export type Clarity = 'high' | 'medium' | 'low' | 'unknown';

export interface NormalizedDocument {
    id: string;
    filename: string;
    doc_type: string;
    extracted_text?: string | null;
    source_url: string;
    thumbnail_url?: string | null;
    processing_status: 'uploaded' | 'stored' | 'preview_ready' | 'classified' | 'cv_pending' | 'cv_complete' | 'mapped' | 'failed' | 'not started' | 'processing' | 'complete';
    is_mock?: boolean;
    source_kind?: 'uploaded' | 'extracted_from_zip' | 'generated_fixture' | string;
    ingested_at?: string;
    extraction_method?: string;
    confidence?: number;
}

export interface PhotoEvidence {
    id: string;
    url: string;
    thumbnail_url?: string;
    type: PhotoType;
    damage_area?: string | null;
    clarity: Clarity;
    processing_status?: 'uploaded' | 'stored' | 'preview_ready' | 'classified' | 'cv_pending' | 'cv_complete' | 'mapped' | 'failed' | 'not started' | 'processing' | 'complete';
    is_mock?: boolean;
    source_kind?: 'uploaded' | 'extracted_from_zip' | 'generated_fixture' | string;
    ingested_at?: string;
    extraction_method?: string;
    confidence?: number;
}

export interface EvidenceMatrix {
    processing_status?: 'not started' | 'processing' | 'complete' | 'partial' | 'failed';
    documents?: NormalizedDocument[];
    photos: PhotoEvidence[];
    missing_required_photos: string[];
    photo_sufficiency_score: number;
}

// 7. Finding
export type Severity = 'critical' | 'major' | 'minor' | 'high' | 'medium' | 'low';
export type RuleTier = 'compliance' | 'logic' | 'intelligence';
export type FindingStatus = 'open' | 'confirmed' | 'overturned' | 'needs_review' | 'deferred';

export interface EvidenceRef {
    id: string;
    type: string;
    source_id?: string | null;
    label: string;
    support_status: 'full' | 'partial' | 'missing';
    reason: string;
    page_or_image?: string | null;
    url?: string | null;
    thumbnail_url?: string | null;
    confidence?: number | null;
    linked_tags?: string[];
    is_mock?: boolean;
}

export interface HistoricalSignal {
    type: 'historically_validated' | 'recommendation_risk' | 'historically_overturned' | 'carrier_historically_overturned' | 'carrier_recommendation_risk' | 'carrier_historically_validated';
    message: string;
}

export interface ActionPlaybook {
    primary_action: string;
    steps: string[];
    escalate_if: string[];
    do_not_do: string[];
}

export interface CarrierGuidelineCitation {
    carrier: string;
    version_label: string;
    section_title: string;
    excerpt: string;
    citation_reference: string;
}

export interface Finding {
    id: string;
    rule_id: string;
    severity: Severity;
    category: string;
    message: string;
    affected_lines: number[];
    evidence_refs: EvidenceRef[];
    recommended_action: string;
    status: FindingStatus;
    financial_impact?: number;
    confidence?: number;
    is_supplement_issue?: boolean;
    
    // Hermes / User fields
    hermes_critique?: string | null;
    guideline_citation?: string | null;
    auditor_outcome?: 'confirm' | 'edit' | 'dismiss' | null;
    auditor_reason_code?: string | null;
    auditor_comment?: string | null;
    
    // Hermes AI Engine Fields
    hermes_recommended_action?: 'approve' | 'dismiss' | 'review' | null;
    hermes_confidence_level?: 'high' | 'medium' | 'low' | null;
    hermes_short_reason?: string | null;
    hermes_rationale_summary?: string | null;
    final_recommendation_text?: string | null;
    advisory_tone?: string | null;
    escalation_hint?: string | null;
    template_family?: string | null;
    wording_variant?: string | null;
    strength_label?: string | null;
    primary_reason_code?: string | null;
    reason_codes_json?: any;
    hermes_version?: string | null;
    
    // Pattern Detection & Playbook
    pattern_detection_flags?: string[];
    pattern_related_lines?: number[];
    action_playbook?: ActionPlaybook;
    triage_priority_score?: number;
    triage_bucket?: string;
    carrier_guideline_citation?: CarrierGuidelineCitation;
    historical_signals?: HistoricalSignal[];
    
    // Phase 5: Recommendation Fields
    suggested_action_type?: string;
    suggested_revision?: Record<string, any>;
    requires_manual_confirmation?: boolean;
    supporting_reason?: string;
}

// 8. Rule Result
export interface RuleResult {
    rule_id: string;
    passed: boolean;
    points_deducted: number;
    rationale: string;
}

// 9. Scorecard
export interface CategoryScores {
    structural_integrity: number;
    line_item_support: number;
    parts_accuracy: number;
    labor_reasonableness: number;
    documentation_readiness: number;
    carrier_compliance: number;
}

export interface Scorecard {
    overall_score: number;
    verdict: 'Pass' | 'Review' | 'Fail';
    category_scores: CategoryScores;
    confidence: number;
}

// 10. Narrative Block
export interface NarrativeBlock {
    damage_summary: string;
    claim_summary: string;
    reviewer_notes: string;
    escalation_note: string;
}

// 11. Reviewer Feedback
export interface ReviewerAction {
    finding_id: string;
    action: 'confirm' | 'override' | 'defer';
    reason_code?: string | null;
    comment?: string | null;
    timestamp?: string | null;
}

export interface ReviewerFeedback {
    actions: ReviewerAction[];
    audit_duration_seconds: number;
    final_verdict?: string | null;
}

// 11.5 Activity Log
export interface ActivityEvent {
    id: string;
    timestamp: string;
    actor: 'system' | 'auditor';
    event_type: string;
    description: string;
    metadata_context?: Record<string, any> | null;
}

// 12. Audit Run
export interface HermesTask {
    id: string;
    finding_id: string;
    line_number: number;
    label: string;
    severity: string;
    score_impact: number;
    status: 'pending' | 'resolved';
    allowed_actions: string[];
}

export interface HermesTaskQueue {
    tasks: HermesTask[];
    total_tasks: number;
    resolved_tasks: number;
}

export interface AuditRun {
    run_id: string;
    timestamp: string;
    status: 'not_started' | 'in_review' | 'needs_follow_up' | 'escalated' | 'completed';
    active_supplement?: string;
    blockers: string[];
    activity_log: ActivityEvent[];
    
    // Hermes Integration
    hermes_status?: 'pending' | 'processing' | 'success' | 'failed' | 'skipped';
    hermes_version_applied?: string;
    advisory_banners?: Array<{ type: 'warning' | 'secondary' | 'info' | 'error'; title: string; message: string }>;
    manual_review_mode?: boolean;
    hermes_tasks?: HermesTaskQueue;
    
    // Core Modality
    claim_package: ClaimPackage;
    file_inventory: FileInventory;
    vehicle_profile: VehicleProfile;
    shop_profile: ShopProfile;
    estimate_lines: EstimateLines;
    evidence_matrix: EvidenceMatrix;
    
    // Processed Outputs
    findings: Finding[];
    rule_results: RuleResult[];
    scorecard: Scorecard;
    narrative: NarrativeBlock;
    reviewer_feedback: ReviewerFeedback;
}

// --- Legacy Types for UI Safety During Transition ---
export type ClaimData = AuditRun;
export type Issue = Finding;
export type ParsedEstimateData = AuditRun;
export interface ClaimHeader {
  claimNumber: string;
  carrier: string;
  status: 'New' | 'In Review' | 'Approved' | 'Escalated';
  riskLevel: 'high' | 'medium' | 'low';
  photoSufficiencyScore: number;
  reportedSeverity: 'minor' | 'moderate' | 'severe';
  drivable: boolean;
  impactArea: string[];
}
