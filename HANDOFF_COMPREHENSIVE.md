# PrimoAuditAI v2 — Comprehensive Technical Handoff

## Project Overview

PrimoAuditAI is an auto damage estimate audit system with two modules:
- **QC Module** — Quality control gateway: admin completeness, photo verification, carrier confidence scoring
- **Audit Module** — Deep line-by-line analysis with AI-powered photo cross-referencing

**Repository:** `https://github.com/primolocal/primoauditai.git` (branch: `v2`)
**Tech Stack:** FastAPI (Python 3.11) + Next.js 14 + PostgreSQL + Ollama (vision)

---

## Architecture

```
Frontend (Next.js 14)          Backend (FastAPI)              Infrastructure
├── /qc/upload                 ├── POST /api/qc               ├── Railway (dev/demo)
├── /qc/[id]                   ├── GET  /api/qc/{id}          ├── PostgreSQL
├── /audit                     ├── POST /api/vision/*         ├── Ollama (local)
└── /api routes                └── EMS ZIP parser             └── Docker Compose (prod)
```

**Database Schema:** Auto-created on startup via SQLAlchemy Alembic migrations.
Tables: `qc_packets`, `qc_findings`, `qc_photos`, `audit_results`

---

## What Works (Production Ready)

### QC Module — Fully Functional

**Upload Flow:**
1. `POST /api/qc` accepts:
   - `estimate_pdf` (required) — CCC ONE estimate
   - `image_pdf` (optional) — separate PDF with photos
   - `ems_zip` (optional) — structured CCC EMS data
   - Checkboxes: vin_photo_present, odometer_photo_present, damage_photos_present

2. Parser extracts: shop info, deductible, insurance, vehicle, state, ZIP, line items
3. Rules engine runs 14 QC rules
4. Carrier confidence score calculated (0-100)
5. Auto-rejects on: missing photos, missing shop, missing deductible
6. Frontend shows findings with Accept/Override/Reject toggles
7. Score recalculates in real-time as findings are dispositioned
8. Auditor note field with Copy button
9. Training dataset export endpoint (`GET /api/qc/dataset/export`)

**QC Rules (14 total):**
| ID | Category | Description |
|---|---|---|
| PHOTOCOV_001 | completeness | VIN photo missing |
| PHOTOCOV_002 | completeness | Odometer photo missing |
| PHOTOCOV_003 | completeness | Damage photos missing |
| COMPLETE_001 | completeness | Deductible missing |
| COMPLETE_007 | completeness | Repair Facility/Shop of Choice missing (AUTO-REJECT) |
| COMPLETE_008 | completeness | Insurance info missing (AUTO-REJECT) |
| EXCEP_002 | exceptions | Manual entry (#) found |
| EXCEP_003 | exceptions | Aftermarket parts on supplements only |
| STATE_001 | state | State missing from estimate |
| STATE_002 | state | TX total loss threshold (75%) |
| TAX_001 | tax | Tax rate mismatch vs reference data |
| LABOR_001 | labor | Labor rate >15% above prevailing |
| SUPP_001 | supplement | Supplement version detection |
| SUPP_002 | supplement | Shop of Choice detection |

**Reference Data:** All 50 states + DC populated with:
- Labor rates ($48-85/hr) based on CCC/Mitchell prevailing data
- Tax rates (Tax Foundation 2024 combined rates)
- ZIP-level overrides for major metros

**EMS ZIP Parser:** (`src/parser/ems_parser.py`)
- Opens CCC EMS ZIP files
- Parses DBF tables for structured metadata
- Eliminates all PDF extraction issues
- Pulls: shop info, labor rate, tax rate, vehicle data, insurance, deductible

### Vision Pipeline — Backend Working

**Damage Detection:**
- Model: `llama3.2-vision:11b` (7.8 GB, downloaded and verified working)
- Endpoint: `POST /api/vision/analyze` (single photo)
- Endpoint: `POST /api/vision/analyze-batch` (multiple photos)
- Endpoint: `POST /api/vision/audit-photos` (PDF → extract → cross-reference)

**Photo Classification:**
- Aspect ratio + dimension heuristics classify photos as: `vin`, `odometer`, `damage`, `other`
- Vision model analyzes damage photos for type: dent, scratch, crack, broken, rust
- Cross-references against estimate line items by panel name matching

**Mock Detector:** Falls back to random realistic data if Ollama unavailable. Same API contract.

### CarDD Integration — Ready for Training

- Dataset downloaded: 4,000 images, 6 damage categories
- Wrapper: `src/cardd_inference.py` (standby, needs GPU + MMDetection)
- To activate: set `CARDD_REPO_PATH` and `CARDD_WEIGHTS_PATH` env vars

---

## What's Broken / Needs Fixing

### 1. Photos Tab on QC Detail Page (CRITICAL)

**Status:** Backend works perfectly. Frontend build fails repeatedly.

**What works:**
- `POST /api/qc` with `image_pdf` extracts photos, classifies them, saves to disk, stores in DB
- `GET /api/qc/{id}` returns photos array with `thumbnail` (base64 JPEG), `photo_type`, `matched_lines`
- Photos are persisted and retrievable

**What's broken:**
- Frontend `src/app/qc/[id]/page.tsx` — Photos tab JSX corrupted by repeated patches
- Build error: orphaned JSX fragments, mismatched braces, undefined variables (`activeTab`, `typeBadge`)
- **Current state:** Photos tab completely removed to get a clean build

**What needs to happen:**
Rebuild the QC detail page with a proper Photos tab:

```tsx
// In src/app/qc/[id]/page.tsx

// Add state (around line 98)
const [activeTab, setActiveTab] = useState<"review" | "photos">("review");

// Add tab bar (after the carrier score card, before the main content)
<div className="mb-4 flex gap-1 border-b border-[#21262d]">
  <button onClick={() => setActiveTab("review")} 
    className={activeTab === "review" ? "active-tab-styles" : "inactive-tab-styles"}>
    Review
  </button>
  <button onClick={() => setActiveTab("photos")}
    className={activeTab === "photos" ? "active-tab-styles" : "inactive-tab-styles"}>
    Photos ({packet.photos?.length || 0})
  </button>
</div>

// Wrap existing two-column grid in: {activeTab === "review" && (<div>...</div>)}

// Add photos tab content:
{activeTab === "photos" && (
  <div>
    <h3>Extracted Photos ({packet.photos?.length || 0})</h3>
    <div className="grid grid-cols-3 gap-3">
      {packet.photos?.map((p) => (
        <div key={p.id}>
          <img src={p.thumbnail} style={{ maxHeight: 200 }} />
          <div>
            <span>{p.photo_type}</span>
            {p.matched_lines?.length > 0 && <span>L{p.matched_lines.join(", ")}</span>}
          </div>
        </div>
      ))}
    </div>
  </div>
)}
```

**Important:** Do NOT patch the existing file. The existing file has 3+ layers of corrupted JSX. Start fresh or restore from the clean commit `1e59198` and add the tab properly in one shot.

**Required: Add image PDF field to upload page**

In `src/app/qc/page.tsx`, the upload form needs a second file input:
```tsx
<input type="file" accept=".pdf" onChange={(e) => setImagePdf(e.target.files?.[0] || null)} />
```
And append it to FormData:
```tsx
if (imagePdf) formData.append("image_pdf", imagePdf);
```

### 2. Vision Model Response Parsing

**Status:** Working with llama3.2-vision:11b, but response format varies.

**Current prompt** returns simple JSON: `{"damage": true, "type": "scratch", "location": "door"}`
**Expected format** in code: structured detections array.

**Fix needed:** The detector normalizes the simple response to the standard format, but this should be made more robust. Consider parsing both formats.

### 3. Frontend Build Warnings

- `npm audit` shows 9 vulnerabilities (4 moderate, 4 high, 1 critical)
- Next.js lockfile missing SWC dependencies — run `npm install` locally to patch
- Railway strips devDependencies — move `tailwindcss`, `autoprefixer`, `postcss` to `dependencies`

---

## Environment Variables

```bash
# Backend (.env)
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db
API_KEYS=your_api_key_here
CORS_ALLOWED_ORIGINS=https://your-domain.com
UPLOAD_DIR=/app/uploads
OLLAMA_HOST=http://localhost:11434
VISION_MODEL=llama3.2-vision:11b

# Frontend (.env.local)
NEXT_PUBLIC_API_URL=https://your-api-domain.com
NEXT_PUBLIC_APP_NAME=PrimoAuditAI
```

---

## File Structure

```
/home/tommy/primoauditai-v2/
├── backend/
│   ├── src/
│   │   ├── api/
│   │   │   ├── app.py                 # FastAPI app factory
│   │   │   ├── routes/
│   │   │   │   ├── qc.py             # QC endpoints (14 rules, scoring)
│   │   │   │   ├── audit.py          # Audit endpoints
│   │   │   │   ├── photos.py         # Photo extraction
│   │   │   │   └── vision.py         # Vision analysis endpoints
│   │   ├── parser/
│   │   │   ├── pdf_estimate_parser.py  # CCC PDF → structured data
│   │   │   └── ems_parser.py           # EMS ZIP → structured data
│   │   ├── rules/
│   │   │   ├── qc_rules.py           # 14 QC rule implementations
│   │   │   ├── qc_scorer.py          # Carrier confidence scoring
│   │   │   └── reference_data.py     # Labor/tax rates (50 states)
│   │   ├── services/
│   │   │   ├── damage_detector.py    # Ollama vision + mock fallback
│   │   │   └── audit_vision.py       # Photo ↔ estimate cross-reference
│   │   ├── photo_extractor.py        # PDF → image extraction
│   │   └── cardd_inference.py        # CarDD trained model wrapper
│   ├── tests/testfiles/              # Test PDFs (TestEstimate.pdf, TestImages.pdf)
│   └── requirements.txt
├── frontend/
│   └── src/app/
│       ├── qc/page.tsx               # Upload form (needs image_pdf field)
│       ├── qc/[id]/page.tsx          # Detail page (needs Photos tab rebuilt)
│       ├── audit/page.tsx            # Audit upload
│       └── audit/[id]/page.tsx       # Audit detail
├── HANDOFF.md                        # Previous handoff doc
└── README.md
```

---

## Next Steps (Priority Order)

1. **Fix Photos Tab** — Rebuild `src/app/qc/[id]/page.tsx` with proper tab navigation and photo grid. Add `image_pdf` field to upload form.
2. **Test End-to-End** — Upload estimate + image PDF, verify photos appear, verify vision classification, verify line matching.
3. **Polish QC Rules** — Based on real-world usage, adjust thresholds (tax rate tolerance, labor rate margin).
4. **Audit Module UI** — Build the audit detail page for deep line-by-line analysis with AI findings.
5. **CarDD Training** — When GPU available, train on company data and swap vision model.

---

## Contact / Questions

- **Repository:** `https://github.com/primolocal/primoauditai` (branch `v2`)
- **Deploy target:** Internal company infrastructure (Docker Compose or Kubernetes)
- **Model hosting:** Ollama runs locally; for production, consider dedicated GPU node
- **Database:** PostgreSQL 14+ with asyncpg driver

---

*Generated: 2026-06-18*
*Last commit on v2: 53191f2 (clean build after photos tab removal)*
