"""
QC endpoint — instant rules-engine-only audit with file parsing.
"""
import time
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, File, HTTPException, UploadFile

from src.engine.context import AuditContext
from src.engine.engine import get_engine
from src.parser.ems_parser import EmsParser
from src.parser.pdf_estimate_parser import PDFEstimateParser
from src.schemas import FindingResponse, QCResponse

router = APIRouter(prefix="/api/qc", tags=["qc"])


def _parse_file(file: UploadFile) -> AuditContext:
    """Parse uploaded file into AuditContext."""
    content = file.file.read()
    filename = file.filename or ""

    if filename.lower().endswith(".zip"):
        parser = EmsParser()
        result = parser.parse(content)
    elif filename.lower().endswith(".pdf"):
        parser = PDFEstimateParser()
        result = parser.parse(content)
    else:
        raise HTTPException(status_code=400, detail="Unsupported file type. Upload .pdf or .zip")

    return result.to_audit_context()


@router.post("", response_model=QCResponse)
async def run_qc(
    estimate_pdf: UploadFile = File(None),
    ems_zip: UploadFile = File(None),
) -> QCResponse:
    """Run a quick audit — parse file, run rules engine, instant return, no DB write."""
    start = time.time()

    file = estimate_pdf or ems_zip
    if not file:
        raise HTTPException(status_code=400, detail="No file uploaded")

    ctx = _parse_file(file)

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
            "lines_parsed": len(ctx.lines),
        },
        processed_at=datetime.now(UTC),
    )
