# PrimoAuditAI v2 — Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.
> **Architecture consultant:** Claude Code (kimi-k2.6 via Ollama) + Antigravity design principles

**Goal:** Rebuild PrimoAuditAI from scratch — preserve all 53 rules and Tommy's audit brain, but with clean architecture, TDD from line 1, and a proper modern UI.

**Architecture:** Decoupled FastAPI backend + Next.js 14 frontend. Domain-driven rules organization. PostgreSQL 16 from day 1 with Alembic migrations. OpenAPI-generated TypeScript client binding frontend to backend. Railway (backend/DB) + Vercel (frontend) deployment.

**Tech Stack:**
- Backend: FastAPI 0.110+, Python 3.11+, Pydantic v2, Uvicorn 0.27+, SQLAlchemy 2.0, asyncpg, Alembic 1.13+
- Frontend: Next.js 14 (App Router), React 18, TypeScript 5.3+, Tailwind CSS 3.4, shadcn/ui, Node 20 LTS
- Database: PostgreSQL 16
- Testing: pytest 8 + pytest-asyncio (backend), Vitest + Playwright (frontend)
- Deployment: Railway (backend/DB), Vercel (frontend)
- Vision: qwen3-vl:235b via Ollama Cloud

---

## Phase 0: Project Scaffolding & Infrastructure

### Task 0.1: Create project root + monorepo structure

**Objective:** Initialize the v2 project directory with monorepo layout

**Files:**
- Create: `/home/tommy/primoauditai-v2/` (root)
- Create: `/home/tommy/primoauditai-v2/CLAUDE.md`
- Create: `/home/tommy/primoauditai-v2/.gitignore`
- Create: `/home/tommy/primoauditai-v2/.env.example`
- Create: `/home/tommy/primoauditai-v2/README.md`

**Directory tree:**
```
primoauditai-v2/
├── backend/
│   ├── src/
│   │   ├── api/            # FastAPI app, routes, middleware
│   │   ├── core/           # Config, cache, logging
│   │   ├── domains/        # Domain-driven rules
│   │   │   ├── audit/      # Core audit rules
│   │   │   ├── natgen/     # NatGen carrier rules
│   │   │   ├── supplement/ # Supplement rules
│   │   │   ├── state/      # State-specific rules
│   │   │   ├── hail/       # Hail/PDR rules
│   │   │   ├── vision/     # Photo evidence rules
│   │   │   └── tommy/      # Tommy's audit brain
│   │   ├── engine/         # Rules engine + auto-discovery
│   │   ├── parser/         # CCC DBF + PDF parsers
│   │   ├── models/         # SQLAlchemy models
│   │   ├── repositories/  # Data access layer
│   │   └── services/       # Business logic services
│   ├── tests/
│   │   ├── domains/        # Per-domain test suites
│   │   ├── engine/
│   │   ├── api/
│   │   └── conftest.py
│   ├── alembic/
│   ├── requirements.txt
│   ├── pyproject.toml
│   └── railway.json
├── frontend/
│   ├── src/
│   │   ├── app/            # Next.js App Router pages
│   │   ├── components/     # shadcn/ui components
│   │   ├── lib/            # API client, utils, types
│   │   └── styles/
│   ├── tests/
│   ├── package.json
│   ├── tsconfig.json
│   ├── tailwind.config.ts
│   └── next.config.js
├── docker-compose.yml
└── .github/workflows/
```

```bash
mkdir -p /home/tommy/primoauditai-v2/{backend/{src/{api,core,domains/{audit,natgen,supplement,state,hail,vision,tommy},engine,parser,models,repositories,services},tests/{domains,engine,api},alembic/versions},frontend/{src/{app,components,lib,styles},tests},.github/workflows}
```

### Task 0.2: Initialize git + write CLAUDE.md

**Objective:** Git init, write the project CLAUDE.md with full tech stack, conventions, and design tokens

**Files:**
- Create: `/home/tommy/primoauditai-v2/CLAUDE.md`
- Run: `git init && git add -A && git commit -m "chore: initialize PrimoAuditAI v2 monorepo"`

### Task 0.3: Backend — Python project setup

**Objective:** Create pyproject.toml, requirements.txt, and virtual environment

**Files:**
- Create: `/home/tommy/primoauditai-v2/backend/pyproject.toml`
- Create: `/home/tommy/primoauditai-v2/backend/requirements.txt`

**requirements.txt:**
```
fastapi==0.110.0
uvicorn[standard]==0.27.0
pydantic==2.6.0
sqlalchemy[asyncio]==2.0.25
asyncpg==0.29.0
alembic==1.13.0
httpx==0.27.0
python-multipart==0.0.9
pydantic-settings==2.1.0
orjson==3.9.12
pymupdf==1.23.0
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4

# Dev
pytest==8.0.0
pytest-asyncio==0.23.0
pytest-xdist==3.5.0
httpx==0.27.0
factory-boy==3.3.0
faker==23.0.0
ruff==0.2.0
mypy==1.8.0
```

### Task 0.4: Frontend — Node.js project setup

**Objective:** Create Next.js 14 project with TypeScript, Tailwind, shadcn/ui

**Files:**
- Create: `/home/tommy/primoauditai-v2/frontend/package.json`
- Create: `/home/tommy/primoauditai-v2/frontend/tsconfig.json`
- Create: `/home/tommy/primoauditai-v2/frontend/next.config.js`
- Create: `/home/tommy/primoauditai-v2/frontend/tailwind.config.ts`
- Create: `/home/tommy/primoauditai-v2/frontend/postcss.config.js`

### Task 0.5: Docker Compose + PostgreSQL

**Objective:** docker-compose.yml with PostgreSQL 16 + FastAPI + Next.js services

**Files:**
- Create: `/home/tommy/primoauditai-v2/docker-compose.yml`

### Task 0.6: CI/CD — GitHub Actions

**Objective:** GitHub Actions workflow: lint, test, type-check on every push

**Files:**
- Create: `/home/tommy/primoauditai-v2/.github/workflows/ci.yml`

---

## Phase 1: Core Engine (TDD from line 1)

### Task 1.1: BaseRule abstract class + RuleResult

**Objective:** Define the rule interface and result type — the foundation everything builds on

**Files:**
- Create: `backend/src/engine/base.py`
- Test: `backend/tests/engine/test_base.py`

**TDD Flow:**
1. Write test: `test_rule_result_creation` — verify RuleResult has id, category, severity, description, line_numbers, confidence
2. Write test: `test_base_rule_applies_raises_not_implemented` — verify BaseRule.applies() raises NotImplementedError
3. Write test: `test_base_rule_evaluate_raises_not_implemented` — verify BaseRule.evaluate() raises NotImplementedError
4. Implement `RuleResult` dataclass
5. Implement `BaseRule` ABC with `applies(ctx) -> bool` and `evaluate(ctx) -> List[RuleResult]`
6. Run tests → all pass
7. Commit: `feat: add BaseRule ABC + RuleResult dataclass`

### Task 1.2: AuditContext data class

**Objective:** The shared context object passed to every rule — wraps parsed estimate data

**Files:**
- Create: `backend/src/engine/context.py`
- Test: `backend/tests/engine/test_context.py`

**TDD Flow:**
1. Write test: `test_audit_context_creation` — verify context accepts lines, panels, metadata
2. Write test: `test_audit_context_get_all_lines` — returns flat list of all lines
3. Write test: `test_is_hail_claim` — detects hail from loss description
4. Write test: `test_is_supplement` — detects supplement from doc type
5. Write test: `test_total_estimate` — sums all line totals
6. Write test: `test_shop_state` — extracts state from shop address
7. Implement `AuditContext` with properties and helpers
8. Run tests → all pass
9. Port helpers from v1 `audit_context.py`
10. Commit: `feat: add AuditContext with shared helpers`

### Task 1.3: Rules engine — auto-discovery + singleton

**Objective:** The engine that finds, loads, caches, and executes all rules

**Files:**
- Create: `backend/src/engine/discovery.py`
- Create: `backend/src/engine/engine.py`
- Test: `backend/tests/engine/test_discovery.py`
- Test: `backend/tests/engine/test_engine.py`

**TDD Flow:**
1. Write test: `test_discover_rules_finds_concrete_rules` — create temp rule files, verify they're found
2. Write test: `test_discover_rules_ignores_abstract` — BaseRule not included
3. Write test: `test_singleton_cache_returns_same_instances` — second call returns cached
4. Write test: `test_engine_runs_all_rules`
5. Write test: `test_per_rule_error_isolation` — one broken rule doesn't crash engine
6. Implement `importlib`-based auto-discovery
7. Implement singleton `RulesEngine` with `_discovered_rules` cache
8. Implement `run_all(ctx) -> Dict[str, List[RuleResult]]`
9. Run tests → all pass
10. Commit: `feat: add rules engine with auto-discovery + singleton cache`

---

## Phase 2: Domain-Driven Rules (Port from v1 archive)

### Task 2.1: Port AUDIT rules (AUDIT_001-010)

**Objective:** Port core audit rules from v1 archive to v2 domain structure — one rule per test, TDD

**Files:**
- Create: `backend/src/domains/audit/__init__.py`
- Create: `backend/src/domains/audit/rules.py` — AUDIT_001 through AUDIT_010
- Test: `backend/tests/domains/audit/test_audit_rules.py`

**Rules to port:**
- AUDIT_001: Labor rate verification
- AUDIT_002: Part price markup check
- AUDIT_003: Overlap detection
- AUDIT_004: Unnecessary operations
- AUDIT_005: Duplicate lines
- AUDIT_006: Missing required operations
- AUDIT_007: Negative labor (with overlap/deduction filtering)
- AUDIT_008: Labor without hours (with flat-rate exclusion)
- AUDIT_009: Paint material calculation
- AUDIT_010: Miscellaneous charge validation

**Source:** `/home/tommy/primoauditai-v1-archive/backend/rules/audit_rules.py`

### Task 2.2: Port NATGEN rules (NATGEN_001-024)

**Objective:** Port all NatGen carrier compliance rules

**Files:**
- Create: `backend/src/domains/natgen/__init__.py`
- Create: `backend/src/domains/natgen/rules.py` — NATGEN_001 through NATGEN_024
- Test: `backend/tests/domains/natgen/test_natgen_rules.py`

**Key rules with v1 false positive fixes built in:**
- NATGEN_001: Scan — 0.5hr is ALLOWED; only flag >0.5hr or un-invoiced
- NATGEN_002/003: Calibration — tighter keyword detection (no "park sensor" false matches)
- NATGEN_004: OEM parts — only when non-OEM used where OEM required
- NATGEN_006: Replace vs repair — not supported threshold
- NATGEN_012: Clear coat — skip individual; only flag 3+ refinish panels
- NATGEN_014: Flex additive — remove when not applicable
- NATGEN_015: Blend — verify adjacent panels
- NATGEN_020: LKQ parts — verify availability

**Source:** `/home/tommy/primoauditai-v1-archive/backend/rules/natgen_rules.py`

### Task 2.3: Port SUPPLEMENT rules (SUPP_001-008)

**Objective:** Port supplement documentation rules

**Files:**
- Create: `backend/src/domains/supplement/__init__.py`
- Create: `backend/src/domains/supplement/rules.py`
- Test: `backend/tests/domains/supplement/test_supplement_rules.py`

**Source:** `/home/tommy/primoauditai-v1-archive/backend/rules/supplement_rules.py`

### Task 2.4: Port STATE rules (STATE_001-003)

**Objective:** Port state-specific compliance rules

**Files:**
- Create: `backend/src/domains/state/__init__.py`
- Create: `backend/src/domains/state/rules.py`
- Test: `backend/tests/domains/state/test_state_rules.py`

**Source:** `/home/tommy/primoauditai-v1-archive/backend/rules/state_rules.py`

### Task 2.5: Port HAIL rules (HAIL_001-002 + Dent Wizard matrix)

**Objective:** Port hail/PDR rules with Dent Wizard matrix data

**Files:**
- Create: `backend/src/domains/hail/__init__.py`
- Create: `backend/src/domains/hail/rules.py`
- Create: `backend/src/domains/hail/dent_wizard_matrix.py`
- Test: `backend/tests/domains/hail/test_hail_rules.py`

**Source:** `/home/tommy/primoauditai-v1-archive/backend/rules/hail_rules.py` + `dent_wizard_matrix.py`

### Task 2.6: Port remaining rules (MOTOR, RACED, RATE, VISION, CHECKLIST, LEARNING)

**Objective:** Port all remaining rule categories

**Files:**
- Create: `backend/src/domains/` — motor, raced, rate, vision, checklist, learning directories
- Test: `backend/tests/domains/` — matching test suites

### Task 2.7: Port Tommy's Audit Brain (8 rules + Communication Playbook)

**Objective:** Port Tommy's proprietary rules and 15 Communication Playbook templates

**Files:**
- Create: `backend/src/domains/tommy/__init__.py`
- Create: `backend/src/domains/tommy/rules.py` — PAINT_001, TL_001, SUPP_008, FRAME_001, ALIGN_001, CHECK_006, HAIL_002, ESCALATE_001
- Create: `backend/src/domains/tommy/playbook.py` — 15 approved response templates
- Test: `backend/tests/domains/tommy/test_tommy_rules.py`
- Test: `backend/tests/domains/tommy/test_playbook.py`

**Source:** `/home/tommy/primoauditai-v1-archive/backend/rules/tommy_audit_rules.py` + `return_comments.py`

---

## Phase 3: API Layer

### Task 3.1: FastAPI app factory + middleware stack

**Objective:** Create the FastAPI application with enterprise middleware from day 1

**Files:**
- Create: `backend/src/api/app.py` — FastAPI creation, middleware, lifespan
- Create: `backend/src/api/middleware/request_id.py`
- Create: `backend/src/api/middleware/auth.py` — API key auth
- Create: `backend/src/api/middleware/rate_limit.py`
- Create: `backend/src/core/config.py` — Pydantic Settings
- Create: `backend/src/core/logging.py` — Structured logging
- Test: `backend/tests/api/test_middleware.py`

**Middleware order (critical):**
1. RequestIDMiddleware
2. CORSMiddleware
3. RateLimitMiddleware
4. APIKeyMiddleware

### Task 3.2: Audit routes — upload, run, status, findings

**Objective:** Core audit API endpoints

**Files:**
- Create: `backend/src/api/routes/audit.py`
- Test: `backend/tests/api/test_audit_routes.py`

**Endpoints:**
- `POST /api/audit/upload` — Upload estimate file (PDF/ZIP)
- `POST /api/audit/{id}/run` — Execute audit (rules engine)
- `GET /api/audit/{id}` — Audit status + metadata
- `GET /api/audit/{id}/findings` — Grouped findings
- `POST /api/audit/{id}/findings/{finding_id}/decide` — Three-state decision (CONFIRMED/QUESTIONABLE/OVERRIDE)
- `GET /api/audit/{id}/scores` — Audit scores per category
- `GET /api/audit/{id}/narrative` — Auto-generated narrative

### Task 3.3: Vision routes — photo extraction + analysis

**Objective:** Photo extraction from PDF + qwen3-vl vision analysis

**Files:**
- Create: `backend/src/api/routes/vision.py`
- Test: `backend/tests/api/test_vision_routes.py`

### Task 3.4: OpenAPI schema + TypeScript client generation

**Objective:** Generate TypeScript fetch client from FastAPI's OpenAPI schema

**Files:**
- Create: `frontend/src/lib/api-client.ts` — generated client
- Script: `backend/scripts/generate-client.sh`

---

## Phase 4: Database Layer

### Task 4.1: SQLAlchemy models

**Objective:** Define all database models with SQLAlchemy 2.0 ORM

**Files:**
- Create: `backend/src/models/audit.py` — Audit, AuditRun, Finding
- Create: `backend/src/models/base.py` — DeclarativeBase, mixins
- Create: `backend/src/models/__init__.py`

### Task 4.2: Repository layer

**Objective:** Data access layer — all queries live here, never in routes

**Files:**
- Create: `backend/src/repositories/audit_repo.py`
- Create: `backend/src/repositories/finding_repo.py`
- Test: `backend/tests/repositories/test_audit_repo.py`

### Task 4.3: Alembic migrations

**Objective:** Initial migration + migration workflow

**Files:**
- Initialize: `backend/alembic/`
- Create: First migration for all initial tables

---

## Phase 5: Parser Layer

### Task 5.1: CCC ONE DBF parser

**Objective:** Port the binary DBF parser from v1

**Files:**
- Create: `backend/src/parser/ccc_dbf.py`
- Test: `backend/tests/parser/test_ccc_dbf.py`

### Task 5.2: PDF estimate parser

**Objective:** Parse PDF-based estimates (non-CCC formats)

**Files:**
- Create: `backend/src/parser/pdf_estimate.py`
- Test: `backend/tests/parser/test_pdf_estimate.py`

### Task 5.3: Evidence parser (photo extraction)

**Objective:** Extract embedded JPEGs from PDF evidence files using PyMuPDF

**Files:**
- Create: `backend/src/parser/evidence.py`
- Test: `backend/tests/parser/test_evidence.py`

---

## Phase 6: Frontend — Next.js Dashboard

### Task 6.1: Shell — sidebar + topbar + layout

**Objective:** App shell with collapsible sidebar, topbar, command palette

**Files:**
- Create: `frontend/src/app/layout.tsx`
- Create: `frontend/src/components/layout/sidebar.tsx`
- Create: `frontend/src/components/layout/topbar.tsx`
- Create: `frontend/src/components/layout/app-shell.tsx`
- Create: `frontend/src/lib/store.ts` — Zustand store

### Task 6.2: Dark theme + design tokens

**Objective:** Tommy's dark theme: #0d1117 bg, #c9d1d9 text, #f0883e accent, 14px base

**Files:**
- Create: `frontend/src/app/globals.css` — Tailwind + CSS variables
- Create: `frontend/src/lib/theme.ts`

### Task 6.3: Upload page

**Objective:** File upload with drag-and-drop, progress, validation

**Files:**
- Create: `frontend/src/app/page.tsx` — Upload landing
- Create: `frontend/src/components/upload/file-uploader.tsx`

### Task 6.4: Findings workspace

**Objective:** Grouped findings display with three-state decision buttons

**Files:**
- Create: `frontend/src/app/audit/[id]/page.tsx`
- Create: `frontend/src/components/findings/finding-card.tsx`
- Create: `frontend/src/components/findings/finding-group.tsx`
- Create: `frontend/src/components/findings/decision-bar.tsx`

### Task 6.5: Photo viewer

**Objective:** Photo viewer with tags, reordering, full-view

**Files:**
- Create: `frontend/src/components/photos/photo-viewer.tsx`
- Create: `frontend/src/components/photos/photo-checklist.tsx`

### Task 6.6: Dashboard / analytics

**Objective:** Audit summary dashboard with stats, charts, history

**Files:**
- Create: `frontend/src/app/dashboard/page.tsx`
- Create: `frontend/src/components/dashboard/stat-card.tsx`
- Create: `frontend/src/components/dashboard/audit-history.tsx`

---

## Phase 7: Services & Vision Pipeline

### Task 7.1: Vision analysis service

**Objective:** qwen3-vl:235b integration for photo evidence verification

**Files:**
- Create: `backend/src/services/vision.py`
- Test: `backend/tests/services/test_vision.py`

### Task 7.2: Learning service

**Objective:** Confidence scoring, candidate generation, feedback loop

**Files:**
- Create: `backend/src/services/learning.py`
- Test: `backend/tests/services/test_learning.py`

### Task 7.3: Narrative service

**Objective:** Auto-generated audit narratives from Communication Playbook templates

**Files:**
- Create: `backend/src/services/narrative.py`
- Test: `backend/tests/services/test_narrative.py`

---

## Phase 8: Deployment

### Task 8.1: Railway backend deployment

**Objective:** Deploy FastAPI backend + PostgreSQL on Railway

**Files:**
- Create: `backend/railway.json`
- Create: `backend/Procfile`

### Task 8.2: Vercel frontend deployment

**Objective:** Deploy Next.js frontend on Vercel

### Task 8.3: GitHub Actions CI/CD

**Objective:** Full CI/CD pipeline — lint, test, type-check, deploy

---

## Key Architecture Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Backend framework | FastAPI | Rules engine is Python; rewriting for Node = catastrophic |
| Frontend framework | Next.js 14 (decoupled) | Modern build pipeline, typed client from OpenAPI |
| Database | PostgreSQL 16 from day 1 | No midway migration pain |
| ORM | SQLAlchemy 2.0 + asyncpg | Fully typed queries, async native |
| Migrations | Alembic from first commit | v1's biggest scar |
| Rules organization | Domain-driven directories | 53 rules flat = unmaintainable |
| API ↔ Frontend binding | OpenAPI-generated TypeScript client | Breaking changes fail at build time |
| Testing | TDD from line 1 — pytest + Vitest + Playwright | Retrofitting tests on 53 rules was brutal |
| Caching | In-memory singleton (Redis later) | v1 pattern worked; scale when needed |
| Error isolation | Per-rule try/except | v1 pattern — keep it |
| Auto-discovery | importlib.pkgutil scanning | v1 pattern — keep it |
| Secrets | .env, never in git, never hardcoded | Non-negotiable |

## Open Questions for Tommy

1. **New project name?** PrimoAuditAI v2? Something else?
2. **GitHub repo?** New repo or same `primolocal/primoauditai` with v2 branch?
3. **Railway project?** New Railway project or same with v2 service?
4. **Vision model?** Stay with qwen3-vl:235b or explore alternatives?
5. **Multi-tenancy?** Single auditor (Tommy) or multi-auditor with accounts?
