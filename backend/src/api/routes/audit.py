"""
Audit routes — upload, run, get, list audits.

POST /api/audits — accepts multipart file upload, parses, persists to DB,
runs rules engine, and returns full audit with findings.
"""
import hashlib
import uuid
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.engine.context import AuditContext
from src.engine.engine import get_engine
from src.models.models import AuditRun, Document, Finding, Photo
# EMS parser disabled for now — revert when needed
# from src.parser.ems_parser import EmsParser
from src.parser.pdf_estimate_parser import PDFEstimateParser, PDFPhotoExtractor
from src.schemas import (
    AuditListResponse,
    AuditResponse,
    FindingResponse,
    FindingUpdate,
)

router = APIRouter(prefix="/api/audits", tags=["audits"])


def _parse_file(content: bytes, filename: str) -> tuple[Any, str]:
    """Parse file bytes into ParsedEstimate and detect type."""
    if filename.lower().endswith(".zip"):
        # EMS parser disabled — return unsupported for now
        raise HTTPException(status_code=400, detail="EMS ZIP parsing is disabled. Upload a PDF estimate.")
    elif filename.lower().endswith(".pdf"):
        parser = PDFEstimateParser()
        result = parser.parse(content)
        return result, "pdf_estimate"
    else:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type. Upload .pdf or .zip"
        )


@router.post("", response_model=AuditResponse, status_code=201)
async def create_audit(
    estimate_pdf: UploadFile | None = File(None),
    ems_zip: UploadFile | None = File(None),
    claim_number: str | None = Form(None),
    vin: str | None = Form(None),
    vehicle_year: int | None = Form(None),
    vehicle_make: str | None = Form(None),
    vehicle_model: str | None = Form(None),
    odometer: int | None = Form(None),
    insurance_company: str | None = Form(None),
    shop_name: str | None = Form(None),
    shop_address: str | None = Form(None),
    loss_description: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
) -> AuditResponse:
    """Create a new audit — parse file, run rules engine, persist results."""
    file = estimate_pdf or ems_zip
    if not file:
        raise HTTPException(status_code=400, detail="No file uploaded. Provide estimate_pdf or ems_zip.")

    # Read file once, reuse bytes
    content = await file.read()

    # Parse file
    parsed, doc_type = _parse_file(content, file.filename or "")
    meta = parsed.metadata
    ctx = parsed.to_audit_context()

    # Build AuditRun — form metadata overrides parsed metadata
    run = AuditRun(
        id=uuid.uuid4(),
        claim_number=claim_number or meta.get("claim_number"),
        vin=vin or meta.get("vin"),
        vehicle_year=vehicle_year or meta.get("vehicle_year"),
        vehicle_make=vehicle_make or meta.get("vehicle_make"),
        vehicle_model=vehicle_model or meta.get("vehicle_model"),
        odometer=odometer or meta.get("odometer"),
        insurance_company=insurance_company or meta.get("insurance_company"),
        shop_name=shop_name or meta.get("shop_name"),
        shop_address=shop_address or meta.get("shop_address"),
        document_type=doc_type,
        loss_description=loss_description or meta.get("loss_description"),
        status="processing",
        total_estimate=ctx.total_estimate(),
        total_labor=ctx.total_labor(),
        total_parts=ctx.total_parts(),
        parsed_lines=parsed.lines,
        parsed_panels=parsed.panels,
        parsed_metadata=meta,
    )
    db.add(run)
    await db.flush()  # Get run.id without committing yet

    # Persist Document record
    doc_hash = hashlib.sha256(content).hexdigest()
    doc = Document(
        id=uuid.uuid4(),
        audit_run_id=run.id,
        filename=file.filename or "unknown",
        file_type=doc_type,
        file_size=len(content),
        content_hash=doc_hash,
    )
    db.add(doc)

    # Extract and persist photos (PDF only)
    if doc_type == "pdf_estimate" and content:
        extractor = PDFPhotoExtractor()
        extracted_photos = extractor.extract(content)
        for photo in extracted_photos:
            p = Photo(
                id=uuid.uuid4(),
                audit_run_id=run.id,
                filename=photo["filename"],
                data_url=photo.get("data_url"),
                tags=[],
                vision_result=None,
            )
            db.add(p)

    # Run unified rules engine — v1 engine + comprehensive QC ruleset
    engine = get_engine()
    raw_results = engine.run_all(ctx)
    
    # Also run the comprehensive QC ruleset (100+ rules)
    from src.rules.qc_rules import run_qc_rules
    qc_findings = run_qc_rules(
        parsed_lines=parsed.lines,
        parsed_metadata=meta,
        photos=[],
        vin_present=False,
        odo_present=False,
        damage_present=False,
        is_supplement=meta.get("is_supplement", False),
    )
    
    # Merge QC findings into the findings list
    findings_count = 0
    passed_count = 0
    seen_rules = set()  # deduplicate by rule_id
    
    # V1 engine findings
    for _rule_name, results in raw_results.items():
        for r in results:
            if r.applies:
                findings_count += 1
                seen_rules.add(r.rule_id)
                finding = Finding(
                    id=uuid.uuid4(),
                    audit_run_id=run.id,
                    rule_id=r.rule_id,
                    category=r.category,
                    severity=r.severity,
                    description=r.description,
                    line_numbers=r.line_numbers,
                    confidence=r.confidence,
                    applies=r.applies,
                    override_reason=r.override_reason,
                )
                db.add(finding)
            else:
                passed_count += 1
    
    # QC ruleset findings (unified 100+ rules)
    for qf in qc_findings:
        rid = qf.get("rule_id", "")
        if rid not in seen_rules:
            findings_count += 1
            seen_rules.add(rid)
            finding = Finding(
                id=uuid.uuid4(),
                audit_run_id=run.id,
                rule_id=rid,
                category=qf.get("category", "general"),
                severity=qf.get("severity", "medium"),
                description=qf.get("description", ""),
                line_numbers=qf.get("line_numbers", []),
                confidence=qf.get("confidence", 1.0),
                applies=True,
            )
            db.add(finding)
    
    run.findings_count = findings_count
    run.passed_count = passed_count
    run.failed_count = findings_count
    run.status = "completed"
    await db.commit()
    await db.refresh(run)

    return AuditResponse.model_validate(run)


@router.get("", response_model=AuditListResponse)
async def list_audits(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> AuditListResponse:
    """List audits with pagination."""
    offset = (page - 1) * page_size

    total_result = await db.execute(select(AuditRun))
    total = len(total_result.scalars().all())

    stmt = select(AuditRun).order_by(AuditRun.created_at.desc()).offset(offset).limit(page_size)
    result = await db.execute(stmt)
    items = result.scalars().all()

    return AuditListResponse(
        items=[AuditResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{audit_id}", response_model=AuditResponse)
async def get_audit(
    audit_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> AuditResponse:
    """Get a single audit by ID with findings."""
    result = await db.execute(select(AuditRun).where(AuditRun.id == audit_id))
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Audit not found")
    return AuditResponse.model_validate(run)


@router.get("/{audit_id}/findings", response_model=list[FindingResponse])
async def get_audit_findings(
    audit_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> list[FindingResponse]:
    """Get findings for a specific audit."""
    stmt = select(Finding).where(Finding.audit_run_id == audit_id).order_by(Finding.created_at.desc())
    result = await db.execute(stmt)
    findings = result.scalars().all()
    return [FindingResponse.model_validate(f) for f in findings]


@router.patch("/{audit_id}/findings/{finding_id}", response_model=FindingResponse)
async def update_finding(
    audit_id: uuid.UUID,
    finding_id: uuid.UUID,
    update: FindingUpdate,
    db: AsyncSession = Depends(get_db),
) -> FindingResponse:
    """Update a finding's status, override reason, or applies flag."""
    stmt = select(Finding).where(
        Finding.id == finding_id,
        Finding.audit_run_id == audit_id,
    )
    result = await db.execute(stmt)
    finding = result.scalar_one_or_none()
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found")

    if update.status is not None:
        finding.status = update.status
    if update.override_reason is not None:
        finding.override_reason = update.override_reason
    elif "override_reason" in update.model_dump(exclude_unset=True):
        finding.override_reason = None
    if update.applies is not None:
        finding.applies = update.applies
        # If auditor marks as not-applies, update audit counts
        if not finding.applies:
            # Recalculate counts
            audit_stmt = select(AuditRun).where(AuditRun.id == audit_id)
            audit_result = await db.execute(audit_stmt)
            audit = audit_result.scalar_one()

            all_findings_stmt = select(Finding).where(Finding.audit_run_id == audit_id)
            all_result = await db.execute(all_findings_stmt)
            all_findings = all_result.scalars().all()

            active = sum(1 for f in all_findings if f.applies)
            overridden = sum(1 for f in all_findings if not f.applies)
            audit.findings_count = active
            audit.passed_count = audit.passed_count + overridden
            audit.failed_count = active

    await db.commit()
    await db.refresh(finding)
    return FindingResponse.model_validate(finding)
