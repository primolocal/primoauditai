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
from src.rules.qc_rules import run_qc_rules
from src.rules.qc_scorer import calculate_carrier_confidence, export_training_dataset

router = APIRouter(prefix="/api/qc", tags=["qc"])

UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "/tmp/primoauditai/qc"))


@router.post("")
async def create_qc(
    request: Request,
    estimate_pdf: UploadFile = File(...),
    image_pdf: UploadFile | None = None,
    ems_zip: UploadFile | None = None,
    vin_photo_present: str = Form("false"),
    odometer_photo_present: str = Form("false"),
    damage_photos_present: str = Form("false"),
) -> dict[str, Any]:
    """Upload estimate PDF (or EMS ZIP), run QC review with manual photo verification."""
    
    vin_present = vin_photo_present.lower() == "true"
    odo_present = odometer_photo_present.lower() == "true"
    damage_present = damage_photos_present.lower() == "true"

    if not estimate_pdf.filename or not estimate_pdf.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="estimate_pdf must be PDF")

    # Read estimate bytes
    est_bytes = await estimate_pdf.read()

    # Parse estimate from PDF
    try:
        parser = PDFEstimateParser()
        parsed = parser.parse(est_bytes)
        parsed_lines = parsed.lines
        parsed_panels = parsed.panels
        parsed_metadata = parsed.metadata
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Failed to parse estimate PDF: {e}")

    # If EMS ZIP provided, override metadata with structured EMS data
    if ems_zip and ems_zip.filename and ems_zip.filename.endswith(".zip"):
        try:
            from src.parser.ems_parser import extract_ems_metadata
            ems_bytes = await ems_zip.read()
            ems_meta = extract_ems_metadata(ems_bytes)
            # EMS metadata overrides PDF-parsed metadata for key fields
            for key in ("shop_name", "shop_address", "shop_phone", "shop_of_choice",
                        "insurance_company", "deductible", "license_plate",
                        "vin", "vehicle_year", "vehicle_make", "vehicle_model",
                        "odometer", "labor_rate", "tax_rate", "state", "zip_code",
                        "loss_date", "loss_description", "claim_number"):
                if ems_meta.get(key) is not None and ems_meta.get(key) != "":
                    parsed_metadata[key] = ems_meta[key]
        except Exception as e:
            # EMS parsing failed — continue with PDF metadata
            pass

    # No image PDF — photos are reviewed manually by QC person
    classified_photos: list[dict[str, Any]] = []
    packet_id = uuid.uuid4()

    # If image PDF provided, extract and label photos using real vision model
    if image_pdf and image_pdf.filename and image_pdf.filename.endswith(".pdf"):
        try:
            from src.photo_extractor import extract_photos_from_pdf
            from src.services.damage_detector import detector as vision
            import base64 as _b64
            from src.services.damage_detector import GeminiVisionDetector, OllamaVisionDetector
            
            img_bytes = await image_pdf.read()
            raw_photos = extract_photos_from_pdf(img_bytes)
            
            for idx, rp in enumerate(raw_photos):
                b64_data = _b64.b64encode(rp["bytes"]).decode() if rp.get("bytes") else ""
                w, h = rp.get("width", 0), rp.get("height", 0)
                
                # Use real vision model (Gemini → Ollama → Mock fallback)
                vision_result = vision.analyze(rp.get("bytes", b""), filename=f"photo_{idx}.jpg")
                ptype = vision_result.get("type", "damage") if vision_result.get("damage") else "other"
                confidence = round(vision_result.get("confidence", 0.5), 2)
                location = vision_result.get("location", "unknown")
                
                # Match to estimate line using vision-detected location + panel keywords
                matched_lines: list[int] = []
                if ptype in ("damage", "dent", "scratch", "crack", "rust") and location:
                    location_lower = location.lower()
                    for line in parsed_lines:
                        panel = (line.get("panel_name") or "").lower()
                        desc = (line.get("description") or "").lower()
                        if panel and not line.get("is_header"):
                            # Check if location appears in panel name or description
                            if any(kw in location_lower for kw in panel.split()) or \
                               any(kw in panel for kw in location_lower.split()):
                                try:
                                    matched_lines.append(int(line["line_no"]))
                                except:
                                    pass
                
                classified_photos.append({
                    "page_num": rp.get("page_num", 0),
                    "image_index": rp.get("image_index", idx + 1),
                    "width": w,
                    "height": h,
                    "photo_type": ptype,
                    "photo_location": location,
                    "confidence": confidence,
                    "matched_lines": matched_lines[:3] or matched_lines[:3] if matched_lines else [],
                    "thumbnail_b64": f"data:image/jpeg;base64,{b64_data}",
                })
        except Exception:
            pass  # Photo extraction failed — continue without photos


    # Run QC rules (returns dicts from to_dict())
    # For supplements, only check lines that were added/changed in THIS supplement
    qc_lines = parsed_lines
    is_supp = parsed_metadata.get("is_supplement", False)
    if is_supp:
        supp_ver = parsed_metadata.get("supplement_version", 0)
        # Match lines with the supplement code S01, S02, etc. matching this version
        target_supp = f"S{supp_ver:02d}"
        qc_lines = [
            ln for ln in parsed_lines
            if ln.get("supplement", "") == target_supp or ln.get("flag") in ("**", "*", "#")
            or ln.get("is_header", False)
        ]
        if len([l for l in qc_lines if not l.get("is_header")]) == 0:
            qc_lines = parsed_lines  # fallback: no supplement-marked lines found

    qc_findings = run_qc_rules(
        qc_lines, parsed_metadata, classified_photos,
        vin_present=vin_present,
        odo_present=odo_present,
        damage_present=damage_present,
        is_supplement=is_supp,
    )

    # Photo counts from checkboxes (human-verified)
    photo_v = 1 if vin_present else 0
    photo_o = 1 if odo_present else 0
    photo_d = 1 if damage_present else 0
    photo_counts = {
        "photo_total": len(classified_photos),
        "photo_vin": photo_v,
        "photo_odometer": photo_o,
        "photo_damage": photo_d,
        "photo_other": max(0, len(classified_photos) - photo_v - photo_o - photo_d),
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
            state=parsed_metadata.get("state") or parsed_metadata.get("vehicle_state"),
            status="completed",
            total_estimate=parsed_metadata.get("total_estimate"),
            parsed_lines=parsed_lines,  # store ALL lines, not just qc_lines
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

        # Add photos with disk storage for GET retrieval
        photo_dir = UPLOAD_DIR / str(packet_id)
        photo_dir.mkdir(parents=True, exist_ok=True)
        import base64 as _b64
        
        for i, p in enumerate(classified_photos):
            # Save photo to disk
            fname = f"photo_{i+1:03d}.jpg"
            fpath = photo_dir / fname
            raw = _b64.b64decode(p.get("thumbnail_b64", "").replace("data:image/jpeg;base64,", ""))
            with open(fpath, "wb") as f:
                f.write(raw)
            
            db.add(QCPhoto(
                id=uuid.uuid4(),
                qc_packet_id=packet_id,
                page_num=p.get("page_num", 0),
                image_index=p.get("image_index", 0),
                filename=fname,
                file_path=str(fpath),
                width=p.get("width", 0),
                height=p.get("height", 0),
                file_size=len(raw),
                photo_type=p.get("photo_type"),
                photo_type_confidence=p.get("confidence", 0.0),
                vision_result={
                    "damage": p.get("photo_type") in ("damage", "dent", "scratch", "crack", "rust", "glass", "tire"),
                    "type": p.get("photo_type"),
                    "confidence": p.get("confidence", 0.0),
                    "location": p.get("photo_location", "unknown"),
                    "matched_lines": p.get("matched_lines", []),
                },
            ))
        
        # Build photo response for POST return
        photo_items_out = [
            {
                "id": str(uuid.uuid4()),
                "filename": f"photo_{idx+1:03d}.jpg",
                "photo_type": p.get("photo_type"),
                "confidence": p.get("confidence", 0.0),
                "photo_location": p.get("photo_location", "unknown"),
                "width": p.get("width", 0),
                "height": p.get("height", 0),
                "page_num": p.get("page_num", 0),
                "image_index": p.get("image_index", idx + 1),
                "matched_lines": p.get("matched_lines", []),
                "thumbnail": p.get("thumbnail_b64"),
            }
            for idx, p in enumerate(classified_photos)
        ]
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
        "rejection_reasons": [r for r in score_result.rejection_reasons if "AUTO-REJECT" in r],
        "auditor_note": score_result.auditor_note,
        "findings": qc_findings,
        "photos": photo_items_out if image_pdf else [],
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
        # Extract vision_result fields if present
        vision = p.vision_result or {}
        photo_items.append({
            "id": str(p.id),
            "filename": p.filename,
            "photo_type": p.photo_type,
            "confidence": p.photo_type_confidence,
            "photo_location": vision.get("location", "unknown"),
            "width": p.width,
            "height": p.height,
            "page_num": p.page_num,
            "image_index": p.image_index,
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
    """Update finding status and recalculate carrier score."""
    if body.status not in ("accepted", "overridden", "rejected"):
        raise HTTPException(status_code=400, detail="Status must be: accepted, overridden, rejected")

    async with async_session() as db:
        result = await db.execute(select(QCFinding).filter(QCFinding.id == uuid.UUID(finding_id)))
        finding = result.scalar_one_or_none()
        if not finding:
            raise HTTPException(status_code=404, detail="Finding not found")

        finding.status = body.status
        await db.flush()

        # Fetch all findings for this packet and recalculate score
        all_res = await db.execute(select(QCFinding).filter(QCFinding.qc_packet_id == uuid.UUID(packet_id)))
        all_findings = all_res.scalars().all()

        pkt_res = await db.execute(select(QCPacket).filter(QCPacket.id == uuid.UUID(packet_id)))
        packet = pkt_res.scalar_one_or_none()

        if packet:
            # Build findings list for scorer — only auto-reject + manually rejected count
            findings_list = [
                {
                    "rule_id": f.rule_id,
                    "category": f.category,
                    "severity": f.severity,
                    "description": f.description,
                    "line_numbers": f.line_numbers,
                }
                for f in all_findings
                if f.status == "rejected"  # only manually rejected count
            ]
            # Always include auto-reject rules unless accepted
            auto_rules = {"COMPLETE_007", "COMPLETE_008", "PHOTOCOV_001", "PHOTOCOV_002", "PHOTOCOV_003"}
            auto_findings = [f for f in all_findings if f.rule_id in auto_rules and f.status != "accepted"]
            
            photo_counts = {
                "photo_total": packet.photo_total,
                "photo_vin": packet.photo_vin,
                "photo_odometer": packet.photo_odometer,
                "photo_damage": packet.photo_damage,
            }
            score_result = calculate_carrier_confidence(
                findings_list + [
                    {"rule_id": f.rule_id, "category": f.category, "severity": f.severity,
                     "description": f.description, "line_numbers": f.line_numbers}
                    for f in auto_findings
                ],
                photo_counts,
                packet.parsed_metadata or {},
            )
            packet.carrier_confidence_score = score_result.total_score
            packet.carrier_ready = score_result.ready_for_carrier
            # Only show auto-reject or manually rejected reasons
            packet.rejection_reasons = score_result.rejection_reasons

        await db.commit()

    return {
        "id": finding_id,
        "status": body.status,
        "carrier_confidence_score": score_result.total_score if packet else 0,
        "carrier_ready": score_result.ready_for_carrier if packet else False,
        "rejection_reasons": score_result.rejection_reasons if packet else [],
    }


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




class PhotoTypeUpdate(BaseModel):
    photo_type: str  # vin, odometer, damage, other


@router.patch("/{packet_id}/photos/{photo_id}/type")
async def update_photo_type(
    packet_id: str,
    photo_id: str,
    body: PhotoTypeUpdate,
    request: Request,
) -> dict[str, Any]:
    """Update photo classification type (manual override)."""
    db = request.app.state.db
    photo = db.query(QCPhoto).filter(
        QCPhoto.id == photo_id,
        QCPhoto.qc_packet_id == packet_id,
    ).first()
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")
    photo.photo_type = body.photo_type
    db.commit()
    db.refresh(photo)
    return {"id": photo.id, "photo_type": photo.photo_type}


@router.patch("/{packet_id}/photos/{photo_id}/location")
async def update_photo_location(
    packet_id: str,
    photo_id: str,
    request: Request,
) -> dict[str, Any]:
    """Update photo damage location (manual override)."""
    body = await request.json()
    new_location = body.get("photo_location", "").strip()
    
    db = request.app.state.db
    photo = db.query(QCPhoto).filter(
        QCPhoto.id == photo_id,
        QCPhoto.qc_packet_id == packet_id,
    ).first()
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")
    
    # Store in vision_result JSON (no schema migration needed)
    vision = dict(photo.vision_result) if photo.vision_result else {}
    vision["location"] = new_location
    photo.vision_result = vision
    db.commit()
    db.refresh(photo)
    return {"id": photo.id, "photo_location": new_location}

@router.get("/dataset/export")
async def export_datasets(request: Request) -> dict[str, Any]:
    """Export all QC training datasets as downloadable JSON."""
    async with async_session() as db:
        result = await db.execute(select(QCPacket).where(QCPacket.training_dataset.isnot(None)))
        packets = result.scalars().all()

    datasets = [p.training_dataset for p in packets if p.training_dataset]
    return {"datasets": datasets, "total": len(datasets)}
