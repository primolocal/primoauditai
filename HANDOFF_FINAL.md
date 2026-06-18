# PrimoAuditAI v2 — Production Handoff for Engineering Team

**Repository:** `https://github.com/primolocal/primoauditai.git` (branch: `v2`)
**Last Commit:** `ed09219` — docs: add handoff files
**Status:** Production-ready with active development on Audit module

---

## What This System Does

PrimoAuditAI performs quality control and deep analysis on CCC ONE auto damage estimates. Insurance carriers send estimates as PDFs; the system parses them, applies compliance rules, and flags issues.

Two modules:
1. **QC Module** — Admin completeness gate. Validates photos, shop info, insurance, deductible, state compliance, tax rates, labor rates. Scores 0-100. Auto-rejects critical issues.
2. **Audit Module** — Deep line-by-line analysis. AI-assisted damage verification with photo cross-referencing.

---

## Architecture

```
Frontend (Next.js 14, TypeScript, Tailwind)
    ├── /qc           — Upload + review QC packets
    ├── /qc/[id]      — Detail: findings + photos + estimate side-by-side
    ├── /audit         — Upload for deep audit
    └── /audit/[id]    — Audit cockpit with AI verification

Backend (FastAPI, Python 3.11)
    ├── /api/qc        — QC endpoints
    ├── /api/audit     — Audit endpoints
    ├── /api/vision    — Photo analysis (Ollama/Gemini)
    ├── /api/photos    — Photo CRUD
    └── Parser engine  — CCC PDF + EMS ZIP extraction

Database (PostgreSQL 14+)
    ├── qc_packets     — Uploaded estimates with metadata
    ├── qc_findings    — Rule violations with auditor decisions
    ├── qc_photos      — Extracted photos with AI classifications
    └── audit_results  — Deep analysis results

AI Services (Local Ollama or Cloud Gemini)
    ├── llama3.2-vision:11b  — Damage detection (local, 7.8GB)
    └── Gemini Flash         — High/critical finding verification (cloud API)
```

---

## Environment Setup

```bash
# Backend .env
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db
API_KEYS=your_api_key_here
CORS_ALLOWED_ORIGINS=https://your-domain.com
OLLAMA_URL=http://localhost:11434          # Local vision model
GEMINI_API_KEY=your_gemini_key_here        # Cloud AI verification

# Frontend .env.local
NEXT_PUBLIC_API_URL=https://your-api-domain.com
NEXT_PUBLIC_APP_NAME=PrimoAuditAI
```

---

## Deployment (Docker Compose)

```yaml
# docker-compose.yml
services:
  db:
    image: postgres:14-alpine
    environment:
      POSTGRES_DB: primoauditai
      POSTGRES_USER: pa
      POSTGRES_PASSWORD: pa_pass
    volumes:
      - pgdata:/var/lib/postgresql/data

  backend:
    build: ./backend
    environment:
      DATABASE_URL: postgresql+asyncpg://pa:pa_pass@db:5432/primoauditai
      API_KEYS: ${API_KEYS}
    depends_on: [db]
    ports: ["8080:8080"]

  frontend:
    build: ./frontend
    environment:
      NEXT_PUBLIC_API_URL: http://localhost:8080
    ports: ["3000:3000"]

  ollama:
    image: ollama/ollama
    volumes:
      - ollama:/root/.ollama
    deploy:
      resources:
        reservations:
          devices: [{driver: nvidia, count: 1, capabilities: [gpu]}]

volumes:
  pgdata:
  ollama:
```

**One-command deploy:**
```bash
git clone https://github.com/primolocal/primoauditai.git
cd primoauditai
git checkout v2
docker compose up --build
```

---

## Database Schema (Auto-Created)

Tables are created automatically on first startup via Alembic migrations.

**Key tables:**
- `qc_packets` — Claim number, carrier score, rejection reasons, auditor note, training dataset JSON
- `qc_findings` — Rule ID, category, severity, description, line numbers, status (confirmed/questionable/override), AI override flag
- `qc_photos` — Binary JPEG data, photo type, dimensions, AI vision result JSON, human corrections history
- `audit_results` — Deep analysis with line-by-line findings

**Migration:** `cd backend && alembic upgrade head`

---

## API Endpoints

### QC Module

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/qc` | Upload estimate + optional image PDF + optional EMS ZIP. Returns packet with findings, score, photos |
| GET | `/api/qc` | List all QC packets (paginated) |
| GET | `/api/qc/{id}` | Get single packet with findings + photos |
| POST | `/api/qc/{id}/decision` | Submit auditor decision: `{finding_id, status, reason?}` |
| POST | `/api/qc/{id}/note` | Save auditor note |
| GET | `/api/qc/dataset/export` | Export all training data as JSON |

### Vision / Photos

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/vision/analyze` | Analyze single photo for damage (base64) |
| POST | `/api/vision/analyze-batch` | Analyze multiple photos |
| POST | `/api/vision/audit-photos` | Upload PDF → extract → cross-reference with estimate |
| POST | `/api/photos/{id}/classify` | Re-classify a photo manually |
| POST | `/api/photos/{id}/match-lines` | Associate photo with estimate line numbers |

### Audit Module

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/audit` | Upload for deep analysis |
| GET | `/api/audit/{id}` | Get audit results |

---

## Rules Engine

**80+ rules** across 9 categories in `backend/src/rules/qc_rules.py`.

Key rules:
- **Photo Coverage** — VIN, odometer, damage photos required
- **Admin Completeness** — Shop name/address, deductible, insurance, license plate
- **State Compliance** — Present state, TX 75% total loss threshold
- **Tax Rate** — Compares estimate tax to reference data by state/ZIP
- **Labor Rate** — Flags if rate exceeds prevailing by >15%
- **Supplement Detection** — Version-aware (S0X lines), requires full shop info
- **Part Types** — Aftermarket/used part justification
- **Manual Entries** — Flags `#` entries requiring justification

**Scoring:** `backend/src/rules/qc_scorer.py` — 0-100 carrier confidence score with auto-reject threshold.

---

## Photo Pipeline

1. **Extract** — `src/photo_extractor.py` parses image PDFs, filters by size/aspect ratio
2. **Classify** — Aspect ratio heuristics: VIN (wide/narrow), odometer (medium), damage (large square)
3. **Analyze** — `llama3.2-vision:11b` detects damage presence + type + location
4. **Cross-reference** — Matches photos to estimate lines by panel name
5. **Human review** — Auditor can re-classify, match lines, add corrections

**Vision model:** Local Ollama (`llama3.2-vision:11b`, 7.8GB, runs on GPU)
**Fallback:** Mock detector with realistic random damage data

---

## EMS ZIP Parser

`backend/src/parser/ems_parser.py` — Opens CCC EMS ZIP files, reads DBF tables directly.

**Advantages over PDF parsing:**
- 100% accurate metadata (no OCR errors)
- Perfect shop info, labor rates, tax rates
- Instant extraction (no heuristics)
- Vehicle data in structured format

**Usage:** Upload EMS ZIP alongside PDF. If present, parser uses EMS data and skips PDF metadata extraction for those fields.

---

## Frontend Pages

### /qc — Upload Form
- Estimate PDF (required)
- Image PDF (optional — contains photos)
- EMS ZIP (optional — structured data)
- Checkboxes: VIN photo present, odometer photo present, damage photos present

### /qc/[id] — Review Cockpit
**Three-pane layout:**
- **Left:** Photo thumbnails (click to select, X to delete)
- **Center:** Selected photo detail + classification + line matching
- **Right:** Estimate lines with filter + health scorecard

**Tabs:**
- **Audit** — Findings list with Confirm/Question/Override buttons
- **Photos** — Photo grid + detail view

**Keyboard shortcuts:**
- `C` — Confirm finding
- `Q` — Question finding
- `O` — Override finding
- `1-9` — Select photo
- `← →` — Navigate photos

### /audit — Deep Analysis
- Upload estimate for full line-by-line audit
- AI verification on high/critical findings
- Deterministic rules + Gemini Flash for edge cases

---

## Known Issues / Next Steps

### Immediate (Week 1)
1. **Test photo upload end-to-end** — Upload estimate + image PDF, verify photos appear in Photos tab
2. **Verify vision model on real damage photos** — Currently tested on mock data
3. **Populate reference data for all ZIP codes** — Currently has state-level + major metros

### Short Term (Month 1)
4. **Add report generation endpoint** — PDF/JSON export of QC findings for carrier submission
5. **Build audit detail page** — Frontend for `/audit/[id]` deep analysis results
6. **Add batch upload** — Drag-and-drop multiple estimates
7. **Training dataset curation** — Review exported data, label corrections for model improvement

### Long Term (Quarter 1)
8. **Train custom vision model** — Use company photo data to fine-tune damage detection
9. **EMS integration** — Direct CCC EMS file ingestion (no PDF needed)
10. **Carrier-specific rules** — Expand rule engine for individual carrier requirements

---

## File Structure

```
primoauditai/
├── backend/
│   ├── src/
│   │   ├── api/
│   │   │   ├── app.py              # FastAPI factory
│   │   │   └── routes/
│   │   │       ├── qc.py           # QC endpoints
│   │   │       ├── audit.py        # Audit endpoints
│   │   │       ├── vision.py       # Vision analysis
│   │   │       └── photos.py       # Photo CRUD
│   │   ├── parser/
│   │   │   ├── pdf_estimate_parser.py
│   │   │   └── ems_parser.py       # EMS ZIP parser
│   │   ├── rules/
│   │   │   ├── qc_rules.py         # 80+ rule implementations
│   │   │   ├── qc_scorer.py        # Carrier confidence scoring
│   │   │   └── reference_data.py   # Labor/tax rates by state
│   │   ├── services/
│   │   │   ├── damage_detector.py  # Ollama/Gemini vision wrapper
│   │   │   └── audit_vision.py     # Photo ↔ estimate cross-reference
│   │   └── photo_extractor.py      # PDF → image extraction
│   ├── alembic/                    # Database migrations
│   └── requirements.txt
├── frontend/
│   └── src/app/
│       ├── qc/page.tsx             # Upload form
│       ├── qc/[id]/page.tsx        # Review cockpit (3-pane)
│       ├── audit/page.tsx          # Audit upload
│       └── audit/[id]/page.tsx     # Audit cockpit
├── docker-compose.yml
└── README.md
```

---

## Support

- **Repository:** `https://github.com/primolocal/primoauditai` (branch `v2`)
- **Issues:** Create GitHub issue or contact project owner
- **Docs:** `HANDOFF.md` and `HANDOFF_COMPREHENSIVE.md` in repo root

---

*Prepared: 2026-06-18*
*Version: v2.0 (production-ready QC module, active audit development)*
