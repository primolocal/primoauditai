"""
QC endpoint — instant rules-engine-only audit. No DB persistence.
"""
import time
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, File, HTTPException, UploadFile

from src.engine.context import AuditContext
from src.engine.engine import get_engine
from src.schemas import FindingResponse, QCResponse

router = APIRouter(prefix="/api/qc", tags=["qc"])


@router.post("", response_model=QCResponse)
async def run_qc(
    estimate_pdf: UploadFile = File(None),
    ems_zip: UploadFile = File(None),
) -> QCResponse:
    """Run a quick audit — rules engine only, instant return, no DB write."""
    start = time.time()

    if not estimate_pdf and not ems_zip:
        raise HTTPException(status_code=400, detail="No file uploaded")

    # TODO: Parse file into AuditContext
    # For now, create empty context + run rules (test mode)
    ctx = AuditContext(lines=[])

    engine = get_engine()
    raw_results = engine.run_all(ctx)

    # Flatten findings
    findings: list[FindingResponse] = []
    passed: list[dict[str, Any]] = []
    severity_counts: dict[str, int] = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
    category_counts: dict[str, int] = {}

    for _rule_name, results in raw_results.items():
        for r in results:
            if r.applies:
                severity_counts[r.severity] = severity_counts.get(r.severity, 0) + 1
                category_counts[r.category] = category_counts.get(r.category, 0) + 1
                findings.append(
                    FindingResponse(
                        id=uuid.uuid4(),
                        rule_id=r.rule_id,
                        category=r.category,
                        severity=r.severity,
                        description=r.description,
                        line_numbers=r.line_numbers,
                        confidence=r.confidence,
                        applies=r.applies,
                        override_reason=r.override_reason,
                        status="unreviewed",
                        created_at=datetime.now(UTC),
                    )
                )
            else:
                passed.append({
                    "rule_id": r.rule_id,
                    "category": r.category,
                    "reason": r.override_reason or "Passed",
                })

    duration = time.time() - start

    return QCResponse(
        findings=findings,
        passed=passed,
        analytics={
            "rule_count": engine.rule_count(),
            "severity_counts": severity_counts,
            "category_counts": category_counts,
            "duration_ms": round(duration * 1000, 2),
        },
        processed_at=datetime.now(UTC),
    )
