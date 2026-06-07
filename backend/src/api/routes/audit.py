"""
Audit routes — upload, run, get, list audits.
"""
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.engine.context import AuditContext
from src.engine.engine import get_engine
from src.models.models import AuditRun, Finding
from src.schemas import (
    AuditCreate,
    AuditListResponse,
    AuditResponse,
    FindingResponse,
)

router = APIRouter(prefix="/api/audits", tags=["audits"])


@router.post("", response_model=AuditResponse, status_code=201)
async def create_audit(
    audit_in: AuditCreate,
    estimate_pdf: UploadFile | None = File(None),
    ems_zip: UploadFile | None = File(None),
    db: AsyncSession = Depends(get_db),
) -> AuditResponse:
    """Create a new audit — parse file, run rules engine, persist results."""
    run = AuditRun(
        id=uuid.uuid4(),
        claim_number=audit_in.claim_number,
        vin=audit_in.vin,
        vehicle_year=audit_in.vehicle_year,
        vehicle_make=audit_in.vehicle_make,
        vehicle_model=audit_in.vehicle_model,
        odometer=audit_in.odometer,
        insurance_company=audit_in.insurance_company,
        shop_name=audit_in.shop_name,
        shop_address=audit_in.shop_address,
        document_type=audit_in.document_type,
        loss_description=audit_in.loss_description,
        status="processing",
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)

    # TODO: Parse uploaded file into AuditContext
    ctx = AuditContext(lines=[])

    # Run rules engine
    engine = get_engine()
    raw_results = engine.run_all(ctx)

    findings_count = 0
    passed_count = 0
    for _rule_name, results in raw_results.items():
        for r in results:
            if r.applies:
                findings_count += 1
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
