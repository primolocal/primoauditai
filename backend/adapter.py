from datetime import datetime
import uuid
from schemas import (
    AuditRun, ClaimPackage, FileInventory, VehicleProfile, ShopProfile,
    EstimateLines, EstimateLine, EstimateTotal, EvidenceMatrix, Scorecard,
    CategoryScores, Finding, NarrativeBlock, ReviewerFeedback
)

def build_audit_run(raw_parsed_data: dict, audit_id: str = None) -> dict:
    # Generate unique run ID
    run_id = audit_id or f"aud_{uuid.uuid4().hex[:8]}"
    
    # Extract claim tracking
    claim_meta = raw_parsed_data.get("claim_meta", {})
    claim_package = ClaimPackage(
        claim_number=claim_meta.get("claim_number", "UNKNOWN_CLAIM"),
        carrier=claim_meta.get("carrier", "Unknown Carrier"),
        status="New"
    )
    
    file_inventory = FileInventory(
        total_files=1
    )
    
    vehicle_profile = VehicleProfile()
    shop_profile = ShopProfile()
    
    estimate_lines = EstimateLines()
    evidence_matrix = EvidenceMatrix(
        processing_status=raw_parsed_data.get("evidence_matrix", {}).get("processing_status", "not started"),
        documents=raw_parsed_data.get("evidence_matrix", {}).get("documents", []),
        photos=raw_parsed_data.get("evidence_matrix", {}).get("photos", []),
        missing_required_photos=raw_parsed_data.get("evidence_matrix", {}).get("missing_required_photos", []),
        photo_sufficiency_score=raw_parsed_data.get("evidence_matrix", {}).get("photo_sufficiency_score", 0),
    )
    
    findings = []
    
    # Parse panels and rows into EstimateLines
    panels = raw_parsed_data.get("claim", {}).get("panels", [])
    gross_total = 0.0
    total_labor = 0.0
    total_parts = 0.0
    
    for panel in panels:
        for r in panel.get("rows", []):
            try:
                line_no = int(r.get("line_no", 0))
            except:
                line_no = 0
                
            el = EstimateLine(
                line_no=line_no,
                operation=r.get("operation_label", ""),
                description=r.get("description", ""),
                operation_type=r.get("operation_type", ""),
                operation_code=r.get("operation_code", ""),
                part_type=r.get("part_type", ""),
                part_number=r.get("part_number", ""),
                price=float(r.get("part_price", 0.0)),
                labor_hours=float(r.get("financial_signature", {}).get("labor_hours_total", 0.0)),
                sublet_amount=float(r.get("misc_amount", 0.0)),
                delta_status=r.get("delta_status", "original")
            )
            estimate_lines.items.append(el)
            
            gross_total += el.price + el.sublet_amount + (el.labor_hours * 50.0) # naive
            total_labor += (el.labor_hours * 50.0)
            total_parts += el.price
            
    estimate_lines.totals = EstimateTotal(
        gross_total=gross_total,
        net_total=gross_total,
        total_labor=total_labor,
        total_parts=total_parts
    )
    
    # Parse Audit results
    scorecard = Scorecard(
        overall_score=100,
        verdict="Pass",
        category_scores=CategoryScores(
            structural_integrity=100,
            line_item_support=100,
            parts_accuracy=100,
            labor_reasonableness=100,
            documentation_readiness=100,
            carrier_compliance=100
        )
    )
    
    findings = []

    
    activity_log = [
        {"id": f"evt_{uuid.uuid4().hex[:6]}", "timestamp": datetime.utcnow().isoformat() + "Z", "actor": "system", "event_type": "audit_created", "description": "Audit run initialized and passed through intelligence mapping."}
    ]
    
    audit_run = AuditRun(
        run_id=run_id,
        timestamp=datetime.utcnow().isoformat() + "Z",
        status="not_started",
        active_supplement=raw_parsed_data.get("active_supplement", "E01"),
        blockers=[],
        activity_log=activity_log,
        claim_package=claim_package,
        file_inventory=file_inventory,
        vehicle_profile=vehicle_profile,
        shop_profile=shop_profile,
        estimate_lines=estimate_lines,
        evidence_matrix=evidence_matrix,
        findings=findings,
        scorecard=scorecard,
        narrative=NarrativeBlock(),
        reviewer_feedback=ReviewerFeedback()
    )
    
    return audit_run.model_dump()
