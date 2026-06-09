# PrimoAuditAI — Comprehensive Audit Rules Reference

**Version:** v3.0 | **Rules:** 40+ | **Scoring:** 200 points (8 categories × 25) | **Pass:** 140/200

---

## Rule Categories

| # | Category | Rules | Description |
|---|----------|-------|-------------|
| 1 | **Photo Coverage** | PHOTOCOV_001–007 | Photo presence, depth, and quality |
| 2 | **Estimate Completeness** | COMPLETE_001–013 | All required metadata fields |
| 3 | **State Compliance** | STATEQC_001–012 | State-specific laws + thresholds |
| 4 | **Exception Handling** | EXCEP_001–005 | Flags, manual entries, A/M, supplements |
| 5 | **Line Item Analysis** | LINE_001–005 | Overlaps, labor, blends, LKQ, CAPA |
| 6 | **Financial Analysis** | FIN_001–004 | Paint materials, ACV, caps, sublets |
| 7 | **Parts Sourcing** | PART_001–003 | Structural safety, OE pricing, LKQ warranty |
| 8 | **Labor Analysis** | LABOR_001–003 | Paint ratio, zero-labor, misc charges |
| 9 | **Rate Verification** | TAX_001, LABOR_001 | Tax + prevailing labor rate checks |

---

## 1. PHOTO COVERAGE (25 pts)

| Rule | Severity | Pts | Auto-Reject | Trigger |
|------|----------|-----|:---:|---------|
| PHOTOCOV_001 | 🔴 HIGH | −25 | ✓ | VIN photo missing |
| PHOTOCOV_002 | 🔴 HIGH | −25 | ✓ | Odometer photo missing |
| PHOTOCOV_003 | 🔴 HIGH | −25 | ✓ | Replace ops but no damage photos |
| PHOTOCOV_004 | 🟢 LOW | — | — | No body operations found with damage photos |
| PHOTOCOV_005 | 🟡 MEDIUM | −5 | — | License plate photo not detected |
| PHOTOCOV_006 | 🟡 MEDIUM | −5 | — | Photo count below panel count |
| PHOTOCOV_007 | 🟢 LOW | −3 | — | No overview/full-vehicle photo |

---

## 2. ESTIMATE COMPLETENESS (25 pts)

| Rule | Severity | Pts | Auto-Reject | Trigger |
|------|----------|-----|:---:|---------|
| COMPLETE_001 | 🟡 MEDIUM | −5 | — | Deductible missing |
| COMPLETE_004 | 🔴 HIGH | −5 | — | Insurance company missing |
| COMPLETE_005 | 🟡 MEDIUM | −3 | — | License plate missing |
| COMPLETE_006 | 🟡 MEDIUM | −2 | — | Odometer missing |
| COMPLETE_007 | 🔴 HIGH | −25 | ✓ | Shop info missing (see table) |
| COMPLETE_008 | 🔴 HIGH | −25 | ✓ | Shop of Choice on supplement |
| COMPLETE_009 | 🔴 HIGH | — | — | VIN not 17 characters |
| COMPLETE_010 | 🟡 MEDIUM | — | — | Year/make/model incomplete |
| COMPL_011 | 🟡 MEDIUM | — | — | Point of impact not recorded |
| COMPL_012 | 🟢 LOW | — | — | Prior damage section empty |
| COMPL_013 | 🟢 LOW | — | — | Production date not on estimate |

### Supplement vs Original — Shop Rules

| | Original | Supplement |
|---|----------|------------|
| Shop info | Name OR Shop of Choice OK | Full name + address required |
| Shop of Choice | Allowed | **AUTO-REJECT** |

---

## 3. STATE COMPLIANCE (25 pts)

| Rule | State | Severity | Trigger |
|------|-------|----------|---------|
| STATEQC_001 | Any | 🔴 HIGH | State not indicated |
| STATEQC_003 | TX | ⛔ CRITICAL | Estimate ≥ 80% of ACV |
| STATEQC_010 | RI | ⛔ CRITICAL | Non-OE part on vehicle < 30 months |
| STATEQC_011 | MN | 🟡 MEDIUM | Non-OE parts without written disclosure |
| STATEQC_012 | WV | ⛔ CRITICAL | A/M structural part on vehicle < 3 years |

---

## 4. EXCEPTION HANDLING (25 pts)

| Rule | Severity | Pts | Suppressed On | Trigger |
|------|----------|-----|---------------|---------|
| EXCEP_001 | 🟡 MEDIUM | −3 | Supplements | Supplement flags (`**`, S01/S02) |
| EXCEP_002 | 🟡 MEDIUM | −3 | Supplements | Manual entries (`#` flag) |
| EXCEP_003 | 🟡 MEDIUM | −8 | Never | A/M or AF parts |
| EXCEP_004 | 🟢 LOW | — | Never | Supplement # > 3 |
| EXCEP_005 | 🟢 LOW | −2 | — | Multiple flag types on same line |

---

## 5. LINE ITEM ANALYSIS (25 pts)

| Rule | Severity | Pts | Trigger |
|------|----------|-----|---------|
| LINE_001 | 🟡 MEDIUM | −8 | Same panel + operation duplicates |
| LINE_002 | 🟢 LOW | −3 | Labor hours < 50% of expected minimum |
| LINE_003 | 🟢 LOW | −3 | Painted panel missing blend on adjacent |
| LINE_004 | 🟢 LOW | −2 | LKQ/USED parts without age/warranty notation |
| LINE_005 | 🟡 MEDIUM | −5 | A/M parts without CAPA certification |

---

## 6. FINANCIAL ANALYSIS (25 pts)

| Rule | Severity | Pts | Trigger |
|------|----------|-----|---------|
| FIN_001 | 🟡 MEDIUM | −5 | Paint labor present but no materials line |
| FIN_002 | 🔴/🟡 | −12/−5 | Estimate ≥ 90%/75% of ACV |
| FIN_003 | 🟡 MEDIUM | −5 | Paint materials > 38% of paint labor |
| FIN_004 | 🟢 LOW | −3 | Sublet operations without invoice |

---

## 7. PARTS SOURCING (25 pts)

| Rule | Severity | Pts | Auto-Reject | Trigger |
|------|----------|-----|:---:|---------|
| PART_001 | ⛔ CRITICAL | −25 | ✓ | A/M part on structural/safety component |
| PART_002 | 🟡 MEDIUM | −3 | — | High-value OE parts (>$2,000) |
| PART_003 | 🟢 LOW | −2 | — | LKQ/used parts without warranty notation |

**Structural panels flagged by PART_001:** frame rail, radiator support, apron, upper/lower rail, inner quarter, rocker panel, B-pillar, A-pillar, cowl, floor pan, firewall, rear body panel, crossmember

---

## 8. LABOR ANALYSIS (25 pts)

| Rule | Severity | Pts | Auto-Reject | Trigger |
|------|----------|-----|:---:|---------|
| LABOR_001 | 🟡 MEDIUM | −5 | — | Paint hours > 3× body hours |
| LABOR_002 | 🔴 HIGH | −12 | ✓ | Zero labor hours on Replace line |
| LABOR_003 | 🟢 LOW | −3 | — | Unitemized/miscellaneous charges |

---

## RATE VERIFICATION (deductions)

| Rule | Severity | Trigger |
|------|----------|---------|
| TAX_001 | 🔴 HIGH | Tax rate differs >0.5% from reference |
| LABOR_001 | 🔴 HIGH | Labor rate >15% above prevailing |

---

## SCORING MODEL

| Score | Status |
|-------|--------|
| **170–200** | ✅ Clean pass — ready for carrier |
| **140–169** | ⚠️ Conditional pass — minor exceptions |
| **0–139** | ❌ Not ready — critical issues |

### Auto-Reject Triggers (instant fail)
1. VIN photo missing
2. Odometer photo missing  
3. Damage photos missing (with Replace ops)
4. Shop info missing (supplement: full info; original: none)
5. Shop of Choice on supplement
6. A/M structural/safety parts
7. Zero labor hours on Replace line

---

## STATE-SPECIFIC RULES

| State | Rule | Requirement |
|-------|------|-------------|
| **TX** | STATEQC_003 | Total loss threshold at 80% of ACV |
| **RI** | STATEQC_010 | OE parts required on vehicles < 30 months |
| **MN** | STATEQC_011 | Written disclosure required for non-OE parts |
| **WV** | STATEQC_012 | OE required for structural parts on vehicles < 3 years |

---

## REFERENCE DATA

### Labor Rates (prevailing)
| State | Default/hr | Major Metro |
|-------|------------|-------------|
| TX | $62 | Dallas $70, Houston $72 |
| CA | $78 | LA $82, SF $85 |
| NY | $78 | NYC $85 |
| FL | $62 | Miami $65 |

### Tax Rates (state + local)
| State | Default | Major Metro |
|-------|---------|-------------|
| TX | 8.25% | — |
| CA | 8.85% | LA 10.25% |
| NY | 8.52% | NYC 8.875% |
| FL | 7.02% | — |
| DE/MT/NH/OR | 0% | No sales tax |

---

## API ENDPOINTS

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/qc` | Upload estimate + image PDF, run all rules |
| GET | `/api/qc` | List all QC packets |
| GET | `/api/qc/{id}` | Get packet detail with findings + photos |
| PATCH | `/api/qc/{id}/photos/{photo_id}/type` | Override photo classification |
| PATCH | `/api/qc/{id}/photos/{photo_id}/location` | Override damage location |
| DELETE | `/api/qc/{id}/photos/{photo_id}` | Remove photo |
| GET | `/api/dataset/export` | Export training data |
| GET | `/api/vision/status` | Active detector type |

---

*Source: `backend/src/rules/qc_rules.py` · `backend/src/rules/qc_scorer.py` · `backend/src/rules/reference_data.py`*
