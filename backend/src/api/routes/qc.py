"""
QC (Quality Control) API Routes
POST /api/qc          — Upload estimate + image PDF, run QC review
GET  /api/qc          — List QC packets
GET  /api/qc/{id}     — Get QC packet detail (includes photo thumbnails)
PATCH /api/qc/{id}/findings/{fid} — Update finding status
"""

import base64
import os
import shutil
import tempfile
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import fitz
from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import async_session
from src.models.models import QCFinding, QCPacket, QCPhoto
from src.parser.pdf_estimate_parser import PDFEstimateParser
from src.photo_extractor import extract_photos_from_pdf, save_photos_to_disk
from src.rules.qc_rules import run_qc_rules
from src.rules.qc_scorer import calculate_carrier_confidence, export_training_dataset

router = APIRouter(prefix="/api/qc", tags=["qc"])

UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "/tmp/primoauditai/qc"))


@router.post("")
async def create_qc(
    request: Request,
    estimate_pdf: UploadFile = File(...),
    vin_photo_present: str = Form("false"),
    odometer_photo_present: str = Form("false"),
    damage_photos_present: str = Form("false"),
) -> dict[str, Any]:
    """Upload estimate PDF, run QC review with manual photo verification."""
    
    vin_present = vin_photo_present.lower() == "true"
    odo_present = odometer_photo_present.lower() == "true"
    damage_present = damage_photos_present.lower() == "true"

    if not estimate_pdf.filename or not estimate_pdf.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="estimate_pdf must be PDF")

    # Read estimate bytes
    est_bytes = await estimate_pdf.read()

    # Parse estimate
    try:
        parser = PDFEstimateParser()
        parsed = parser.parse(est_bytes)
        parsed_lines = parsed.lines
        parsed_panels = parsed.panels
        parsed_metadata = parsed.metadata
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Failed to parse estimate PDF: {e}")

    # No image PDF — photos are reviewed manually by QC person
    classified_photos: list[dict[str, Any]] = []


    # Run QC rules (items tagged as manual_review)
    qc_findings_raw = run_qc_rules(parsed_lines, parsed_metadata, classified_photos)
    qc_findings = [
        {
            "rule_id": f.rule_id,
            "category": f.category,
            "severity": f.severity,
            "description": f.description,
            "line_numbers": list(f.line_numbers) if f.line_numbers else [],
            "confidence": 1.0,
            "applies": f.applies,
            "suggested_fix": f.suggested_fix,
        }
        for f in qc_findings_raw
    ]

    # Photo counts from checkboxes (human-verified)
    photo_counts = {
        "photo_total": len(classified_photos),
        "photo_vin": 1 if vin_present else 0,
        "photo_odometer": 1 if odo_present else 0,
        "photo_damage": 1 if damage_present else 0,
        "photo_other": len(classified_photos) - (int(vin_present) + int(odo_present) + int(damage_present)),
    }

    # Calculate carrier confidence score
    score_result = calculate_carrier_confidence(
        qc_findings,
        photo_counts,
        parsed_metadata,
    )

    # Persist to DB
    async with async_session() as db:
        packet = QCPacket(
            id=packet_id,
            claim_number=parsed_metadata.get("claim_number"),
            vin=parsed_metadata.get("vin"),
            vehicle_year=parsed_metadata.get("year"),
            vehicle_make=parsed_metadata.get("make"),
            vehicle_model=parsed_metadata.get("model"),
            odometer=parsed_metadata.get("odometer"),
            insurance_company=parsed_metadata.get("insurance_company"),
            shop_name=parsed_metadata.get("shop_name"),
            shop_address=parsed_metadata.get("shop_address"),
            deductible=parsed_metadata.get("deductible"),
            state=parsed_metadata.get("state"),
            status="completed",
            total_estimate=parsed_metadata.get("total_estimate"),
            parsed_lines=parsed_lines,
            parsed_panels=parsed_panels,
            parsed_metadata=parsed_metadata,
            **photo_counts,
            carrier_confidence_score=score_result.total_score,
            carrier_ready=score_result.ready_for_carrier,
            rejection_reasons=score_result.rejection_reasons,
            auditor_note=score_result.auditor_note,
        )
        db.add(packet)

        # Add findings
        for f in qc_findings:
            qcf = QCFinding(
                id=uuid.uuid4(),
                qc_packet_id=packet_id,
                rule_id=f["rule_id"],
                category=f["category"],
                severity=f["severity"],
                description=f["description"],
                line_numbers=f.get("line_numbers", []),
                confidence=f.get("confidence", 1.0),
                applies=f.get("applies", True),
                suggested_fix=f.get("suggested_fix"),
            )
            db.add(qcf)

        # Generate training dataset
        await db.flush()

        export_pkt = {
            "id": str(packet_id),
            "created_at": None,
            "parsed_lines": parsed_lines,
            "parsed_metadata": parsed_metadata,
            "photo_total": photo_counts["photo_total"],
            "photo_vin": photo_counts["photo_vin"],
            "photo_odometer": photo_counts["photo_odometer"],
            "photo_damage": photo_counts["photo_damage"],
        }

        dataset = export_training_dataset(export_pkt, qc_findings, score_result)
        packet.training_dataset = dataset

        # Add photos (store thumbnails in DB for later retrieval)
        for p in classified_photos:
            db.add(QCPhoto(
                id=uuid.uuid4(),
                qc_packet_id=packet_id,
                page_num=p.get("page_num", 0),
                image_index=p.get("image_index", 0),
                filename=Path(p["file_path"]).name,
                file_path=p.get("file_path"),
                width=p.get("width", 0),
                height=p.get("height", 0),
                file_size=len(base64.b64decode(p.get("thumbnail_b64", "").replace("data:image/jpeg;base64,", ""))),
                photo_type=p.get("photo_type"),
                photo_type_confidence=p.get("photo_type_confidence", 0.0),
            ))

        await db.commit()

    return {
        "id": str(packet_id),
        "status": "completed",
        "claim_number": parsed_metadata.get("claim_number"),
        "vehicle": f"{parsed_metadata.get('year', '')} {parsed_metadata.get('make', '')} {parsed_metadata.get('model', '')}".strip(),
        "findings_count": len(qc_findings),
        "photo_total": photo_counts["photo_total"],
        "photo_vin": photo_counts["photo_vin"],
        "photo_odometer": photo_counts["photo_odometer"],
        "photo_damage": photo_counts["photo_damage"],
        "carrier_confidence_score": score_result.total_score,
        "carrier_ready": score_result.ready_for_carrier,
        "rejection_reasons": score_result.rejection_reasons,
        "auditor_note": score_result.auditor_note,
        "findings": qc_findings,
    }


@router.get("")
async def list_qc(request: Request) -> dict[str, Any]:
    """List all QC packets."""
    async with async_session() as db:
        result = await db.execute(select(QCPacket).order_by(QCPacket.created_at.desc()))
        packets = result.scalars().all()

    items = []
    for p in packets:
        items.append({
            "id": str(p.id),
            "claim_number": p.claim_number,
            "vehicle": f"{p.vehicle_year or ''} {p.vehicle_make or ''} {p.vehicle_model or ''}".strip(),
            "status": p.status,
            "findings_count": p.findings_count,
            "photo_total": p.photo_total,
            "carrier_confidence_score": p.carrier_confidence_score,
            "carrier_ready": p.carrier_ready,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        })

    return {"items": items, "total": len(items)}


@router.get("/{packet_id}")
async def get_qc(packet_id: str, request: Request) -> dict[str, Any]:
    """Get a single QC packet with findings and photo thumbnails."""
    packet_uuid = uuid.UUID(packet_id)
    async with async_session() as db:
        result = await db.execute(select(QCPacket).filter(QCPacket.id == packet_uuid))
        packet = result.scalar_one_or_none()
        if not packet:
            raise HTTPException(status_code=404, detail="QC packet not found")

        findings_res = await db.execute(select(QCFinding).filter(QCFinding.qc_packet_id == packet_uuid))
        findings = findings_res.scalars().all()

        photos_res = await db.execute(select(QCPhoto).filter(QCPhoto.qc_packet_id == packet_uuid))
        photos = photos_res.scalars().all()

    # Generate thumbnails from saved photo files
    photo_items = []
    for p in photos:
        thumb = None
        if p.file_path and os.path.exists(p.file_path):
            try:
                with open(p.file_path, "rb") as f:
                    raw = f.read()
                b64 = base64.b64encode(raw).decode()
                thumb = f"data:image/jpeg;base64,{b64}"
            except Exception:
                pass
        photo_items.append({
            "id": str(p.id),
            "filename": p.filename,
            "photo_type": p.photo_type,
            "width": p.width,
            "height": p.height,
            "page_num": p.page_num,
            "thumbnail": thumb,
        })

    return {
        "id": str(packet.id),
        "claim_number": packet.claim_number,
        "status": packet.status,
        "vehicle": f"{packet.vehicle_year or ''} {packet.vehicle_make or ''} {packet.vehicle_model or ''}".strip(),
        "findings_count": len(findings),
        "photo_total": packet.photo_total,
        "photo_vin": packet.photo_vin,
        "photo_odometer": packet.photo_odometer,
        "photo_damage": packet.photo_damage,
        "carrier_confidence_score": packet.carrier_confidence_score,
        "carrier_ready": packet.carrier_ready,
        "rejection_reasons": packet.rejection_reasons,
        "auditor_note": packet.auditor_note,
        "parsed_lines": packet.parsed_lines,
        "parsed_metadata": packet.parsed_metadata,
        "findings": [
            {
                "id": str(f.id),
                "rule_id": f.rule_id,
                "category": f.category,
                "severity": f.severity,
                "description": f.description,
                "line_numbers": f.line_numbers,
                "applies": f.applies,
                "status": f.status,
                "suggested_fix": f.suggested_fix,
            }
            for f in findings
        ],
        "photos": photo_items,
    }


class FindingUpdate(BaseModel):
    status: str  # accepted, overridden, rejected


@router.patch("/{packet_id}/findings/{finding_id}")
async def update_finding_status(
    packet_id: str, finding_id: str, body: FindingUpdate, request: Request
) -> dict[str, Any]:
    """Update finding status: accepted, overridden, or rejected."""
    if body.status not in ("accepted", "overridden", "rejected"):
        raise HTTPException(status_code=400, detail="Status must be: accepted, overridden, rejected")

    async with async_session() as db:
        result = await db.execute(select(QCFinding).filter(QCFinding.id == uuid.UUID(finding_id)))
        finding = result.scalar_one_or_none()
        if not finding:
            raise HTTPException(status_code=404, detail="Finding not found")

        finding.status = body.status
        await db.commit()

    return {"id": finding_id, "status": body.status}


class NoteUpdate(BaseModel):
    auditor_note: str


@router.patch("/{packet_id}/note")
async def update_auditor_note(
    packet_id: str, body: NoteUpdate, request: Request
) -> dict[str, Any]:
    """Update auditor note on a QC packet."""
    async with async_session() as db:
        result = await db.execute(select(QCPacket).filter(QCPacket.id == uuid.UUID(packet_id)))
        packet = result.scalar_one_or_none()
        if not packet:
            raise HTTPException(status_code=404, detail="QC packet not found")

        packet.auditor_note = body.auditor_note
        await db.commit()

    return {"id": packet_id, "auditor_note": body.auditor_note}
