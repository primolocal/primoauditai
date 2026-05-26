"""
Full Audit Mode — complete pre-submission review.
Includes photo alignment, NADA/TL threshold, appraiser notes, full checklist.
"""
import uuid, io, re, base64
from typing import List, Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Request
from audit_context import AuditContext
from rules.base import BaseRule, RuleResult

full_audit_router = APIRouter(prefix="/api/audit", tags=["full-audit"])


@full_audit_router.post("/full")
async def run_full_audit(
    request: Request,
    estimate_pdf: UploadFile = File(...),
    nada_value: float = Form(None),
    photos: List[UploadFile] = File(None),
):
    """
    Full pre-submission audit. Includes photo alignment (JPG/PNG or PDF with embedded images),
    NADA/TL comparison, appraiser note generation, and complete file review.
    """
    contents = await estimate_pdf.read()
    
    # Parse estimate
    from parser.pdf_estimate_parser import PDFEstimateParser
    p = PDFEstimateParser()
    parsed_data = p.parse_pdf(io.BytesIO(contents))
    
    # Process photo uploads — extract from PDFs if needed
    photo_images = []
    if photos:
        for photo_file in photos:
            pc = await photo_file.read()
            if photo_file.filename and photo_file.filename.lower().endswith('.pdf'):
                # Extract images from PDF
                try:
                    import fitz
                    doc = fitz.open(stream=pc, filetype="pdf")
                    for page_num in range(len(doc)):
                        for img in doc[page_num].get_images():
                            xref = img[0]
                            base_image = doc.extract_image(xref)
                            photo_images.append({
                                "filename": f"{photo_file.filename}_p{page_num+1}_{xref}.jpg",
                                "data": base_image["image"],
                            })
                    doc.close()
                except Exception:
                    pass
            else:
                photo_images.append({
                    "filename": photo_file.filename or "photo.jpg",
                    "data": pc,
                })
    
    # Run rules engine
    from rules_engine import RulesEngine
    engine = RulesEngine()
    result = engine.evaluate_estimate(parsed_data)
    findings = (
        result.get("audit", {}).get("base_findings", []) +
        result.get("audit", {}).get("carrier_overlays", {}).get("natgen", {}).get("findings", [])
    )
    
    meta = parsed_data.get("claim_meta", {})
    vehicle = meta.get("vehicle", {})
    shop = meta.get("shop", {})
    
    # Detect supplement
    is_supplement = any(
        str(r.get("supplement", "")).upper() not in ("", "E01")
        for p in parsed_data.get("claim", {}).get("panels", [])
        for r in p.get("rows", [])
    )
    
    # --- NADA / TL Threshold ---
    tl_info = _build_tl_info(parsed_data, nada_value, shop.get("state", ""))
    
    # --- Photo alignment ---
    photo_issues = _build_photo_alignment(parsed_data)
    
    # Run vision analysis on uploaded photos if available
    if photo_images:
        photo_issues = _run_vision_analysis(parsed_data, photo_images)
    
    # --- Appraiser notes ---
    appraiser_notes = _build_appraiser_notes(findings, photo_issues, tl_info, meta)
    
    # --- CCC tabs checklist ---
    checklist = _build_checklist(parsed_data, is_supplement)
    
    # --- Generate findings with confidence ---
    from services.audit_presentation import group_findings, build_passed, CONFIDENCE

    groups = group_findings(findings)

    # Build passed
    passed = build_passed(parsed_data, shop, is_supplement)

    # Build rate/tax summary for CCC tabs display
    rate_summary = ""
    tax_comparison = ""
    try:
        import re as _re
        addr = shop.get("address", "")
        zips = _re.findall(r'\b(\d{5})\b', addr)
        if zips:
            from tax_labor_lookup import lookup_labor, lookup_tax
            for z in zips:
                if int(z) > 10000:
                    labor = lookup_labor(z)
                    tax = lookup_tax(z)
                    if labor and labor.get("body", 0) > 0:
                        rate_summary = f"ZIP {z}: Body ${labor['body']}/hr Paint ${labor.get('paint',0)}/hr"
                    if tax and tax.get("combined", 0) > 0:
                        est_tax = parsed_data.get("claim_meta", {}).get("estimate_tax_rate")
                        tax_comparison = f"ZIP {z}: {tax['combined']:.1%}"
                        if est_tax:
                            tax_comparison += f" | Est: {est_tax:.1%}"
                    break
    except Exception:
        pass

    total_findings = len(findings)
    
    return {
        "audit_id": f"full_{uuid.uuid4().hex[:8]}",
        "file_type": "pdf",
        "is_supplement": is_supplement,
        "claim_number": meta.get("claim_number", "?"),
        "vehicle": {
            "year": vehicle.get("year"), "make": vehicle.get("make"),
            "model": vehicle.get("model"), "mileage": vehicle.get("mileage"),
            "vin": vehicle.get("vin"),
        },
        "shop": {
            "name": shop.get("name", ""), "state": shop.get("state", ""),
            "address": shop.get("address", ""), "phone": shop.get("phone", ""),
        },
        "findings": {
            "state": [{"severity": f.get("severity"), "summary": f.get("summary"),
                       "lines": f.get("affected_lines", []),
                       "confidence": CONFIDENCE.get(f.get("rule_id",""), 0.7),
                       "rule_id": f.get("rule_id","")} for f in groups["state"]],
            "remove": [{"severity": f.get("severity"), "summary": f.get("summary"),
                        "lines": f.get("affected_lines", []),
                        "confidence": CONFIDENCE.get(f.get("rule_id",""), 0.7),
                        "rule_id": f.get("rule_id","")} for f in groups["remove"]],
            "fix": [{"severity": f.get("severity"), "summary": f.get("summary"),
                     "lines": f.get("affected_lines", []),
                     "confidence": CONFIDENCE.get(f.get("rule_id",""), 0.7),
                     "rule_id": f.get("rule_id","")} for f in groups["fix"]],
            "verify": [{"severity": f.get("severity"), "summary": f.get("summary"),
                        "lines": f.get("affected_lines", []),
                        "confidence": CONFIDENCE.get(f.get("rule_id",""), 0.7),
                        "rule_id": f.get("rule_id","")} for f in groups["verify"]],
            "attach": [{"severity": f.get("severity"), "summary": f.get("summary"),
                        "lines": f.get("affected_lines", []),
                        "confidence": CONFIDENCE.get(f.get("rule_id",""), 0.7),
                        "rule_id": f.get("rule_id","")} for f in groups["attach"]],
            "review": [{"severity": f.get("severity"), "summary": f.get("summary"),
                        "lines": f.get("affected_lines", []),
                        "confidence": CONFIDENCE.get(f.get("rule_id",""), 0.7),
                        "rule_id": f.get("rule_id","")} for f in groups["review"]],
        },
    "total_findings": total_findings,
    "passed": passed,
    "extracted_photos": [
        {"filename": img["filename"], "data_url": f"data:image/jpeg;base64,{base64.b64encode(img['data']).decode()}"}
        for img in photo_images
    ] if photo_images else [],
        "claim_panels": parsed_data.get("claim", {}).get("panels", []),
        "rate_summary": rate_summary,
        "tax_comparison": tax_comparison,
        "tl_analysis": tl_info,
        "photo_issues": photo_issues,
        "appraiser_notes": appraiser_notes,
        "ccc_checklist": checklist,
    }


def _build_tl_info(parsed_data: dict, nada_value: Optional[float], state: str) -> dict:
    """Build NADA/TL threshold comparison."""
    if not nada_value:
        return {"note": "NADA value not provided — cannot calculate TL position"}
    
    total = sum(
        r.get("financial_signature", {}).get("part_price", 0) +
        r.get("financial_signature", {}).get("labor_amount_total", 0) +
        r.get("financial_signature", {}).get("misc_amount", 0)
        for p in parsed_data.get("claim", {}).get("panels", [])
        for r in p.get("rows", [])
    )
    
    pct = total / nada_value * 100 if nada_value > 0 else 0
    
    tl_thresholds = {
        "KS": 0.75, "NE": 0.75, "MO": 0.80, "OK": 0.60, "TX": 0.80, "LA": 0.75,
        "AR": 0.70, "IA": 0.80, "IL": 0.80, "TN": 0.75, "MS": 0.75, "AL": 0.75,
        "GA": 0.80, "FL": 0.80, "SC": 0.75, "NC": 0.75, "VA": 0.75,
        "PA": 0.80, "NY": 0.75, "OH": 0.75, "MI": 0.75, "IN": 0.80,
        "WI": 0.70, "MN": 0.80, "CO": 0.80, "AZ": 0.80, "NV": 0.65,
        "CA": 1.0, "WA": 0.80, "OR": 0.80, "MT": 0.80,
    }
    threshold = tl_thresholds.get(state.upper(), 0.75)
    
    tl_value = nada_value * threshold
    
    return {
        "nada_value": nada_value,
        "estimate_total": round(total, 2),
        "damage_pct": round(pct, 1),
        "tl_threshold_pct": round(threshold * 100),
        "tl_threshold_value": round(tl_value, 2),
        "status": "POTENTIAL TOTAL LOSS — escalate to carrier" if total >= tl_value else
                  "Approaching threshold" if pct >= threshold * 80 else
                  "Repairable — under threshold",
    }


def _build_photo_alignment(parsed_data: dict) -> list:
    """Check which estimate lines lack photo support."""
    issues = []
    for panel in parsed_data.get("claim", {}).get("panels", []):
        for row in panel.get("rows", []):
            if row.get("is_header"): continue
            op = str(row.get("operation_label", "")).lower()
            desc = str(row.get("description", "")).lower()
            if op in ("include", "", "included"): continue
            has_photo = row.get("evidence_refs") and any(
                e.get("type") == "photo" for e in row.get("evidence_refs", [])
            )
            if not has_photo and op in ("replace", "repair", "pdr", "overhaul"):
                issues.append({
                    "line_no": row.get("line_no"), "operation": op,
                    "description": desc[:80],
                    "issue": "No photo evidence found for this operation",
                    "action": "Verify photo supports this line. If unsupported, remove or add note.",
                })
    return issues


def _run_vision_analysis(parsed_data: dict, photo_images: list) -> list:
    """Run qwen3-vl on uploaded photos and match to estimate lines."""
    import base64, os, httpx, concurrent.futures
    
    ollama_url = os.environ.get("OLLAMA_CLOUD_BASE_URL", "https://ollama.com/v1")
    ollama_key = os.environ.get("OLLAMA_CLOUD_API_KEY", "")
    vision_model = os.environ.get("OLLAMA_CLOUD_VISION_MODEL", "qwen3-vl:235b")
    
    if not ollama_key:
        return _build_photo_alignment(parsed_data)
    
    # Build list of estimate lines for the model to match against
    line_items = []
    for panel in parsed_data.get("claim", {}).get("panels", []):
        for row in panel.get("rows", []):
            if row.get("is_header"): continue
            op = str(row.get("operation_label", "")).lower()
            if op in ("include", "", "included"): continue
            line_items.append(f"L{row.get('line_no')}: {op} {row.get('description','')[:60]}")
    
    line_context = "\n".join(line_items[:30])  # First 30 lines for context
    
    matched_lines = set()
    photo_details = []
    
    def analyze_photo(img_data):
        try:
            b64 = base64.b64encode(img_data["data"]).decode()
            resp = httpx.post(
                f"{ollama_url}/chat/completions",
                headers={"Authorization": f"Bearer {ollama_key}"},
                json={
                    "model": vision_model,
                    "messages": [{
                        "role": "user",
                        "content": [
                            {"type": "text", "text": (
                                "You are an auto damage appraiser. Look at this photo and identify:\n"
                                "1. What panel/area is shown?\n"
                                "2. Is there damage visible? Describe it.\n"
                                "3. What operation would be needed? (replace, repair, pdr, r&i)\n"
                                "4. Does this photo support any of these estimate lines?\n\n"
                                f"{line_context}\n\n"
                                "Respond in JSON: {\"panel\":\"...\",\"damage\":true/false,\"damage_desc\":\"...\","
                                "\"operation\":\"...\",\"supports_lines\":[1,2,...],\"confidence\":0.0-1.0}"
                            )},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                        ]
                    }],
                    "temperature": 0.1, "max_tokens": 300,
                },
                timeout=60,
            )
            if resp.status_code == 200:
                import json
                result = json.loads(resp.json()["choices"][0]["message"]["content"])
                for ln in result.get("supports_lines", []):
                    matched_lines.add(ln)
                return result
        except Exception:
            pass
        return None
    
    # Analyze up to 10 photos in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
        futures = [ex.submit(analyze_photo, img) for img in photo_images[:10]]
        for f in futures:
            try:
                r = f.result(timeout=90)
                if r:
                    photo_details.append(r)
            except Exception:
                pass
    
    # Build issues list — lines NOT matched by any photo
    issues = []
    for panel in parsed_data.get("claim", {}).get("panels", []):
        for row in panel.get("rows", []):
            if row.get("is_header"): continue
            op = str(row.get("operation_label", "")).lower()
            if op in ("include", "", "included"): continue
            ln = row.get("line_no")
            if ln not in matched_lines and op in ("replace", "repair", "pdr", "overhaul"):
                issues.append({
                    "line_no": ln,
                    "operation": op,
                    "description": str(row.get("description", ""))[:80],
                    "issue": "No photo support found by AI vision analysis",
                    "action": "Verify photo supports this line. IF THE PHOTOS DON'T SHOW IT, DO NOT WRITE IT.",
                })
    
    # Add photo count to first issue
    if photo_details:
        issues.insert(0, {
            "line_no": "",
            "operation": "summary",
            "description": f"Vision analyzed {len(photo_images)} photos, matched {len(matched_lines)} estimate lines",
            "issue": f"Photos analyzed: {len(photo_details)} successful. {len(matched_lines)} lines have photo support.",
            "action": "",
        })
    
    return issues


def _build_appraiser_notes(findings: list, photo_issues: list, tl_info: dict, meta: dict) -> list:
    """Generate appraiser communication notes for each finding."""
    notes = []
    
    # TL note
    if tl_info.get("status") == "POTENTIAL TOTAL LOSS — escalate to carrier":
        notes.append({
            "type": "CRITICAL",
            "line": "",
            "note": f"Estimate at {tl_info['damage_pct']}% of NADA value (${tl_info['nada_value']:,.0f}). "
                    f"TL threshold is {tl_info['tl_threshold_pct']}%. This file should be escalated to carrier "
                    f"as potential total loss per NatGen guidelines. Do NOT authorize repair."
        })
    
    # Photo issues
    if photo_issues:
        notes.append({
            "type": "HIGH",
            "line": "",
            "note": f"{len(photo_issues)} line(s) lack photo support. Unsupported lines are the #1 revision trigger. "
                    f"IF THE PHOTOS DON'T SHOW IT, DO NOT WRITE IT."
        })
    
    # Key findings
    for f in findings:
        rid = f.get("rule_id", "")
        if rid in ("NATGEN_014",):
            notes.append({
                "type": "HIGH", "line": str(f.get("affected_lines", [""])[0]),
                "note": f"Flex additive detected — NatGen says NO FLEX. Please remove the flex additive charge.",
            })
        elif rid == "NATGEN_002":
            notes.append({
                "type": "HIGH", "line": str(f.get("affected_lines", [""])[0]),
                "note": f"Calibration on original estimate — defer to supplement per NatGen guidelines.",
            })
    
    # General close
    vehicle = meta.get("vehicle", {})
    notes.append({
        "type": "CLOSE",
        "line": "",
        "note": (
            f"Please review the above items and revise as appropriate. "
            f"Current documentation does not clearly support all operations. "
            f"Please provide supporting rationale or revise. Thank you."
        ),
    })
    
    return notes


def _build_checklist(parsed_data: dict, is_supplement: bool) -> list:
    """Build CCC tab verification checklist."""
    shop = parsed_data.get("claim_meta", {}).get("shop", {})
    vehicle = parsed_data.get("claim_meta", {}).get("vehicle", {})
    
    return [
        {"tab": "Facts of Loss", "check": "Verify facts match assignment", "status": "pending"},
        {"tab": "Claim Type", "check": "Verify claim type and deductible", "status": "pending"},
        {"tab": "Contacts", "check": "Verify contact type and insurance info", "status": "pending"},
        {"tab": "Inspection", "check": f"Verify location: {shop.get('name','?')}",
         "status": "confirm" if shop.get("name") else "pending"},
        {"tab": "Vehicle", "check": f"VIN: {vehicle.get('vin','?')} | Odo: {vehicle.get('mileage','?')}",
         "status": "confirm" if vehicle.get("vin") else "pending"},
        {"tab": "Estimate", "check": "Complete audit report with detailed notes", "status": "pending"},
        {"tab": "Rates", "check": "Verify labor rates and tax per ZIP standard", "status": "pending"},
        {"tab": "Settlements", "check": "Verify repairable vs total loss", "status": "pending"},
        {"tab": "Properties", "check": "Verify refinish/materials/TL thresholds", "status": "pending"},
        {"tab": "Photos", "check": "All required photos present and labeled", "status": "pending"},
    ]
    return checklist
