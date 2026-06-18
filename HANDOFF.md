# PrimoAuditAI v2 — QC Module Technical Handoff

**Prepared:** June 12, 2026  
**Repository:** `https://github.com/primolocal/primoauditai.git` (branch: `v2`)  
**Stack:** FastAPI (Python) + Next.js 14 (TypeScript) + PostgreSQL + Ollama (local vision)

---

## 1. What We Built

A **QC (Quality Control) module** that audits auto damage estimates before they go to carriers. Upload an estimate PDF (and optionally a photo PDF), get a carrier confidence score (0–100), review flagged items with Accept/Override/Reject toggles, and submit.

### Core Features (Working)

| Feature | Status |
|---------|--------|
| Estimate PDF parsing (CCC format) | ✅ |
| Photo extraction from image PDFs | ✅ |
| 14 QC rules with auto-reject logic | ✅ |
| Carrier confidence score + pass/fail | ✅ |
| Accept/Override/Reject toggles | ✅ |
| Score recalculation on toggle | ✅ |
| Auditor note + copy button | ✅ |
| Training dataset export (JSON) | ✅ |
| EMS ZIP parser (structured metadata) | ✅ |
| All 50 states labor/tax reference data | ✅ |
| Vision damage detection (llama3.2-vision) | ✅ |

---

## 2. Architecture

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Next.js 14  │────▶│ FastAPI      │────▶│ PostgreSQL   │
│  (frontend)  │◄────│ (backend)    │◄────│ (data)       │
└──────────────┘     └──────────────┘     └──────────────┘
                            │
                     ┌──────┴──────┐
                     │ Ollama      │
                     │ llama3.2    │
                     │ -vision:11b │
                     └─────────────┘
```

**Backend:** `backend/src/api/routes/qc.py` — main QC endpoint  
**Frontend:** `frontend/src/app/qc/` — upload page + detail page  
**Parser:** `backend/src/parser/pdf_estimate_parser.py` — CCC PDF extraction  
**Photo Extractor:** `backend/src/photo_extractor.py` — extracts images from PDFs  
**Vision:** `backend/src/services/damage_detector.py` — Ollama integration  
**Rules:** `backend/src/rules/qc_rules.py` — 14 QC rules  
**Scorer:** `backend/src/rules/qc_scorer.py` — carrier confidence scoring  
**Reference Data:** `backend/src/rules/reference_data.py` — labor rates + tax rates

---

## 3. API Endpoints

### `POST /api/qc`
Upload an estimate and run QC.

**Form fields:**
- `estimate_pdf` (file, required) — CCC estimate PDF
- `image_pdf` (file, optional) — PDF with embedded damage/VIN/odometer photos
- `ems_zip` (file, optional) — CCC EMS ZIP for structured metadata
- `vin_photo_present` (string: "true"/"false") — manual checkbox
- `odometer_photo_present` (string: "true"/"false") — manual checkbox
- `damage_photos_present` (string: "true"/"false") — manual checkbox

**Response:**
```json
{
  "id": "uuid",
  "claim_number": "12345-1",
  "vehicle_year": 2024,
  "vehicle_make": "Nissan",
  "vehicle_model": "Rogue",
  "state": "TX",
  "carrier_confidence_score": 84,
  "carrier_ready": false,
  "rejection_reasons": ["AUTO-REJECT: ..."],
  "findings": [...],
  "photos": [...]  // if image_pdf uploaded
}
```

### `GET /api/qc/{id}`
Retrieve a QC packet with findings and photos.

### `PATCH /api/qc/{id}/findings/{finding_id}`
Update a finding status: `"accepted"`, `"overridden"`, `"rejected"`.

### `POST /api/qc/{id}/note`
Save auditor note.

### `GET /api/qc/dataset/export`
Export all QC data as training dataset JSON.

---

## 4. Database Schema

### `qc_packets` table
- `id` (UUID, PK)
- `claim_number`, `vehicle_year`, `vehicle_make`, `vehicle_model`
- `state`, `zip_code`
- `insurance_company`, `shop_name`, `shop_address`
- `carrier_confidence_score` (integer)
- `carrier_ready` (boolean)
- `rejection_reasons` (JSON)
- `auditor_note` (text)
- `parsed_lines` (JSON)
- `parsed_metadata` (JSON)
- `training_dataset` (JSON)
- `created_at`, `updated_at`

### `qc_findings` table
- `id` (UUID, PK)
- `qc_packet_id` (FK)
- `rule_id`, `category`, `severity`
- `description`, `line_numbers` (JSON)
- `applies` (boolean), `status` (string)
- `suggested_fix`

### `qc_photos` table
- `id` (UUID, PK)
- `qc_packet_id` (FK)
- `page_num`, `image_index`
- `filename`, `file_path`
- `width`, `height`, `file_size`
- `photo_type` (vin/odometer/damage/other)
- `photo_type_confidence`

---

## 5. QC Rules (14 Total)

### Auto-Reject (hard block)
- **COMPLETE_007** — Repair Facility/Shop of Choice missing
- **COMPLETE_008** — Photos not uploaded (VIN, odometer, or damage)

### Photo Coverage (manual checkbox)
- **PHOTOCOV_001** — VIN photo missing
- **PHOTOCOV_002** — Odometer photo missing
- **PHOTOCOV_003** — Damage photos missing

### Estimate Completeness
- **COMPLETE_001** — No deductible amount listed
- **COMPLETE_002** — No insurance company listed
- **COMPLETE_003** — No license plate or VIN
- **COMPLETE_004** — No odometer reading

### State Compliance
- **STATE_001** — State missing from estimate
- **TX_001** — TX vehicle over $25,000 threshold (requires total loss verification)
- **TAX_001** — Tax rate mismatch vs reference data
- **LABOR_001** — Labor rate > 15% above prevailing rate for ZIP

### Exception Verification (supplements only)
- **EXCEP_002** — Manual entries (#) present
- **EXCEP_003** — Aftermarket parts (A/M) — shop justification needed

---

## 6. Scoring System

```
Base: 100 points
- Photo coverage: -10 per missing photo type
- Completeness: -5 per missing field
- State compliance: -5 per violation
- Tax/labor: -5 per violation
- Supplement exceptions: -5 per item

Auto-reject: score capped at 49, carrier_ready = false
```

Toggling a finding to **Accepted** removes its penalty and recalculates the score.

---

## 7. Photo Pipeline

### Extraction
`photo_extractor.py` uses PyMuPDF to extract embedded images from PDFs:
- Filters images ≥200px wide, aspect ratio < 4:1
- Saves to disk at `{UPLOAD_DIR}/{packet_id}/photo_{NNN}.jpg`

### Classification (heuristic)
- VIN: aspect > 3.0, height < 200px
- Odometer: aspect 1.5–3.0, height < 300px
- Damage: width > 400, height > 300
- Other: everything else

### Vision Analysis (optional — llama3.2-vision:11b)
`damage_detector.py` sends photos to Ollama:
```bash
ollama pull llama3.2-vision:11b  # ~8GB, already pulled
```
Returns:
```json
{"damage": true, "type": "scratch", "location": "right front fender"}
```

### Cross-Reference
Damage photos are matched to estimate lines by panel name (e.g., "RT Fender" → line 5).

---

## 8. EMS ZIP Parser

Optional structured input. Opens EMS ZIP files, parses DBF tables:
- `Veh_Dtl.dbf` → year, make, model, VIN, odometer
- `Repair_Facility.dbf` → shop name, address, type (Shop of Choice)
- `Insurance_Co.dbf` → insurance company
- `Labor_Rate.dbf` → labor rate by operation
- `Sales_Tax.dbf` → tax rate by ZIP

Replaces PDF extraction with 100% accurate structured data.

---

## 9. Reference Data

`reference_data.py` contains:
- **Labor rates** by state + ZIP (all 50 states + DC)
- **Tax rates** by state (combined state + local)
- **ZIP-level overrides** for major metros

Data sources: CCC/Mitchell prevailing rate surveys, Tax Foundation 2024.

---

## 10. Frontend Structure

```
frontend/src/app/qc/
├── page.tsx          # Upload form (estimate + image PDF + checkboxes)
├── [id]/
│   └── page.tsx      # Detail page (findings left, lines right)
```

**Missing:** Photos tab on detail page. Backend returns photos in GET response, frontend just needs to display them.

---

## 11. Deployment

### Backend
```bash
cd backend
pip install -r requirements.txt
export DATABASE_URL="postgresql+asyncpg://user:pass@host:5432/db"
export CORS_ALLOWED_ORIGINS="https://your-domain.com"
export API_KEYS="your-secret-key"
export OLLAMA_HOST="http://localhost:11434"
uvicorn src.api.app:app --host 0.0.0.0 --port 8080
```

### Frontend
```bash
cd frontend
npm install
export NEXT_PUBLIC_API_URL="https://api.your-domain.com"
npm run build
```

### PostgreSQL
Schema auto-creates on first startup. No manual migrations needed.

---

## 12. What's Working vs What's Needed

### ✅ Working
- Upload estimate → parse → score → findings
- Photo extraction from image PDFs
- Vision classification (llama3.2-vision)
- EMS ZIP parser
- All 50 states reference data
- Training dataset export
- Auditor note + copy button

### 🔧 Needs Frontend Work
- **Photos tab** on QC detail page — backend returns photos, frontend needs to render them
- Photo thumbnails should show: image, type badge (vin/odometer/damage), matched line numbers

### 🔧 Needs Backend Work
- **Line matching** — currently heuristic (panel name string match). Needs proper vision → line cross-reference.
- **Batch photo analysis** — analyze all photos in parallel for speed.

### 🚀 Future Enhancements
- Train CarDD model on your own damage photos for better accuracy
- Add supplement version detection (S01, S02, etc.)
- Batch upload multiple estimates
- PDF report generation with findings + photos

---

## 13. Key Files for the Programmer

| File | Purpose |
|------|---------|
| `backend/src/api/routes/qc.py` | Main QC POST/GET/PATCH endpoints |
| `backend/src/rules/qc_rules.py` | 14 QC rules |
| `backend/src/rules/qc_scorer.py` | Scoring logic |
| `backend/src/rules/reference_data.py` | Labor/tax rates |
| `backend/src/parser/pdf_estimate_parser.py` | CCC PDF parser |
| `backend/src/parser/ems_parser.py` | EMS ZIP parser |
| `backend/src/photo_extractor.py` | PDF photo extraction |
| `backend/src/services/damage_detector.py` | Ollama vision integration |
| `frontend/src/app/qc/page.tsx` | Upload form |
| `frontend/src/app/qc/[id]/page.tsx` | Detail page |
| `HANDOFF.md` | This document |

---

## 14. Testing

Upload endpoint:
```bash
curl -X POST https://api.your-domain.com/api/qc \
  -H "X-API-Key: your-key" \
  -F "estimate_pdf=@TestEstimate.pdf" \
  -F "image_pdf=@TestImages.pdf" \
  -F "vin_photo_present=true" \
  -F "odometer_photo_present=true" \
  -F "damage_photos_present=true"
```

Vision test:
```bash
curl -X POST https://api.your-domain.com/api/vision/analyze \
  -H "X-API-Key: your-key" \
  -F "photo=@damage.jpg"
```

---

## 15. Contact

Built by Tommy. Questions: check the repo or refer to this doc.
