# PrimoAuditAI QC Module — Technical Handoff

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌────────────┐
│  Next.js 14     │────▶│  FastAPI (Python) │────▶│ PostgreSQL │
│  Frontend :3000 │     │  Backend :8000    │     │            │
└─────────────────┘     └──────────────────┘     └────────────┘
       │                         │
       ▼                         ▼
  React + Tailwind          PyMuPDF + SQLAlchemy
  shadcn/ui components      Rules engine + scorer
```

- **Frontend**: Next.js 14 (App Router), React 18, Tailwind CSS 3.4, lucide-react icons
- **Backend**: FastAPI, SQLAlchemy 2.0 async, PyMuPDF for PDF parsing
- **Database**: PostgreSQL 16 (auto-creates schema on startup)
- **No AI/LLM dependencies** — pure deterministic rules engine

---

## Repository

**Branch:** `v2`
**Path:** `~/primoauditai-v2/`

### Directory Structure

```
primoauditai-v2/
├── backend/
│   ├── src/
│   │   ├── api/routes/qc.py          # QC endpoints
│   │   ├── models/models.py          # DB models (QCPacket, QCFinding, QCPhoto)
│   │   ├── parser/pdf_estimate_parser.py  # CCC PDF parser
│   │   └── rules/
│   │       ├── qc_rules.py           # QC rules engine (12 rules)
│   │       ├── qc_scorer.py          # Carrier confidence scoring
│   │       └── reference_data.py     # Labor/tax rate tables
│   └── requirements.txt
├── frontend/
│   └── src/app/qc/                   # QC pages
│       ├── page.tsx                  # Upload + list
│       └── [id]/page.tsx             # Detail with findings + toggles
└── .gitignore
```

---

## QC Endpoints

### `POST /api/qc`
Upload estimate PDF for QC review.

**Request:** `multipart/form-data`
| Field | Type | Description |
|-------|------|-------------|
| `estimate_pdf` | file | CCC ONE estimate PDF |
| `vin_photo_present` | string | "true" or "false" |
| `odometer_photo_present` | string | "true" or "false" |
| `damage_photos_present` | string | "true" or "false" |

**Response:**
```json
{
  "id": "uuid",
  "claim_number": "260124150-1",
  "vehicle": "2020 JEEP Cherokee...",
  "findings_count": 5,
  "carrier_confidence_score": 76,
  "carrier_ready": false,
  "rejection_reasons": ["AUTO-REJECT: Repair Facility missing"],
  "auditor_note": "✗ Not ready for carrier...",
  "findings": [...]
}
```

### `GET /api/qc/{id}`
Full packet detail with parsed lines, findings, and photos.

### `PATCH /api/qc/{id}/findings/{finding_id}`
Update finding status. Body: `{"status": "accepted" | "overridden" | "rejected"}`
Recalculates carrier score automatically.

### `PATCH /api/qc/{id}/note`
Update auditor note. Body: `{"auditor_note": "..."}`

### `GET /api/qc/dataset/export`
Export all training datasets as JSON.

---

## QC Rules (12 Rules)

| Rule ID | Category | Description | Auto-Reject |
|---------|----------|-------------|:---:|
| PHOTOCOV_001 | Photo | VIN photo missing | ✓ |
| PHOTOCOV_002 | Photo | Odometer photo missing | ✓ |
| PHOTOCOV_003 | Photo | Damage photos missing | ✓ |
| COMPLETE_001 | Completeness | Deductible not found | — |
| COMPLETE_004 | Completeness | Insurance not listed | — |
| COMPLETE_005 | Completeness | License plate missing | — |
| COMPLETE_006 | Completeness | Odometer not recorded | — |
| COMPLETE_007 | Completeness | Repair Facility missing | ✓ |
| COMPLETE_008 | Completeness | Shop of Choice on supplement | ✓ |
| STATEQC_001 | State | State not indicated | — |
| TAX_001 | State | Tax rate mismatch | — |
| LABOR_001 | State | Labor rate >15% above prevailing | — |

### Supplement Detection
The parser detects supplement version from "Supplement of Record X" in the PDF. For supplements:
- Only lines marked with `S0X` (matching version) are checked
- Full shop name + address required
- Shop of Choice/Owner's Choice = auto-reject on supplements

---

## Carrier Confidence Scoring

**Max:** 100 points
**Pass threshold:** 70
**4 categories (25 pts each):**

| Category | What's scored |
|----------|---------------|
| Photo Coverage | VIN, odometer, damage photos |
| Estimate Completeness | Shop, deductible, insurance, plates, odometer |
| State Compliance | State, tax rate, labor rate |
| Exception Handling | A/M parts, manual entries, flags |

**Auto-reject rules** deduct 25 pts and force `carrier_ready = false` regardless of other scores.

---

## PDF Parsing

The parser (`pdf_estimate_parser.py`) extracts:
| Field | Source |
|-------|--------|
| claim_number | "Claim #:" in header |
| vin | "VIN:" 17-char pattern |
| odometer | "Odometer:" in vehicle section |
| vehicle_year/make/model | "VEHICLE" row |
| shop_name | Repair Facility column (x-coordinate + text fallback) |
| shop_address | Repair Facility column |
| deductible | "Deductible" line in totals |
| license_plate | "License:" in vehicle section |
| insurance_company | "For:" section in header |
| labor_rate | "Labor Rate:" or "Body Labor Rate:" |
| tax_rate | Sales tax percentage in totals |
| is_supplement | "Supplement of Record X" pattern |
| supplement_version | Number from supplement title |

---

## Reference Data

Labor rates and tax rates are in `backend/src/rules/reference_data.py`.
Structure supports state-level defaults + ZIP-level overrides.

**To maintain:** Add new ZIP codes and update rates as needed:
```python
LABOR_RATES = {
    "TX": {
        "default": 62.00,
        "zips": {"76009": 68.00, "75201": 70.00}
    },
    ...
}
TAX_RATES = {
    "TX": {
        "default": 0.0625,
        "zips": {"76009": 0.0825}
    },
    ...
}
```

---

## Training Dataset

Every QC review generates a structured JSON record saved to `QCPacket.training_dataset`. Fields include:
- **Inputs**: vehicle info, shop, state/ZIP, insurance, photo counts, findings
- **Labels**: carrier_confidence_score, ready_for_carrier, rejection_reasons
- **Auditor decision**: auditor_note

Export via the "Export Training Data" button in the UI or `GET /api/qc/dataset/export`.

---

## Environment Variables

### Backend
```
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db
CORS_ALLOWED_ORIGINS=http://localhost:3000,https://your-domain.com
API_KEYS=your_api_key
UPLOAD_DIR=/tmp/primoauditai/qc
```

### Frontend
```
NEXT_PUBLIC_API_URL=https://backend.your-domain.com
```

---

## Deployment

Tested on Railway with:
- **Backend**: `python -m uvicorn src.api.app:app --host 0.0.0.0 --port 8080`
- **Frontend**: `npm install && npm run build` then `npx next start`
- **PostgreSQL**: Railway managed Postgres

Same stack works on Docker, AWS, GCP, or bare metal. Schema auto-creates on startup.

---

## Integration With Internal Systems

### Pulling documents programmatically
Your internal workflow just POSTs the estimate PDF + checkbox values:
```python
import requests

files = {"estimate_pdf": open("estimate.pdf", "rb")}
data = {
    "vin_photo_present": "true",
    "odometer_photo_present": "true",
    "damage_photos_present": "true",
}
resp = requests.post(
    "https://qc-api.your-domain.com/api/qc",
    files=files,
    data=data,
    headers={"X-API-Key": "your_api_key"}
)
result = resp.json()
print(f"Score: {result['carrier_confidence_score']}/100")
print(f"Ready: {result['carrier_ready']}")
```

### Embedding the UI
The Next.js frontend can be iframed into any internal portal. The sidebar navigation can be customized for your workflow.

### Key Integration Points
1. **Document source** — wherever your estimates live, POST them to `/api/qc`
2. **Photo verification** — your QC person checks photos in their existing system, then marks checkboxes
3. **Results** — read findings from the API response, display in your portal, or use the provided UI
4. **Training data** — pull from `/api/qc/dataset/export` to train your own ML models
