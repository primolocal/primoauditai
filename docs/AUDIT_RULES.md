# PrimoAuditAI — QC Audit Rules Reference

**Version:** v2.1 | **Generated:** June 9, 2026 | **Source:** `backend/src/rules/`

---

## Overview

**24 rules** across **6 categories** evaluate every estimate + photo packet. Each produces a finding with severity, description, and suggested fix.

**Scoring:** 150 points total (25 per category). Pass threshold: **105/150** (~70%).

---

## Rule Categories

| Category | Rules | Points | Description |
|----------|-------|--------|-------------|
| **Photo Coverage** | PHOTOCOV_001–004 | 25 | VIN, odometer, and damage photos required |
| **Estimate Completeness** | COMPLETE_001–010 | 25 | Deductible, shop info, insurance, VIN, vehicle info |
| **State Compliance** | STATEQC_001–003 | 25 | State present, TX total loss threshold |
| **Exception Verification** | EXCEP_001–003 | 25 | Supplement flags, manual entries, A/M parts |
| **Line Item Analysis** | LINE_001–004 | 25 | Overlaps, labor hours, blends, LKQ parts |
| **Financial Analysis** | FIN_001–002 | 25 | Paint materials, total vs ACV |
| **Rate Verification** | TAX_001, LABOR_001 | Deductions | Tax rate and labor rate against reference data |

---

## PHOTO COVERAGE RULES

### PHOTOCOV_001 — VIN Missing
| Severity | 🔴 HIGH | **Auto-Reject** YES (−25 pts) |
|----------|---------|-------------------------------|
| **Trigger** | No VIN checkbox AND no photo classified as `vin` |
| **Finding** | VIN photo required but not found in packet |
| **Fix** | Upload VIN plate photo |

### PHOTOCOV_002 — Odometer Missing
| Severity | 🔴 HIGH | **Auto-Reject** YES (−25 pts) |
|----------|---------|-------------------------------|
| **Trigger** | No odometer checkbox AND no photo classified as `odometer` |
| **Finding** | Odometer/mileage photo required but not found |
| **Fix** | Upload dashboard photo showing mileage |

### PHOTOCOV_003 — Damage Photos Missing
| Severity | 🔴 HIGH | **Auto-Reject** YES (−25 pts) |
|----------|---------|-------------------------------|
| **Trigger** | Replace operations found on estimate, but no damage photos |
| **Finding** | Replace operations found (N panels) but no damage photos |
| **Fix** | Upload photos of damaged panels listed in estimate |

### PHOTOCOV_004 — No Panel Operations Found
| Severity | 🟢 LOW |
|----------|--------|
| **Trigger** | Damage photos present but no body/paint operations |
| **Finding** | No body/paint operations found — verify damage photos show all impact areas |

---

## ESTIMATE COMPLETENESS RULES

| Rule | Severity | Points | Trigger | Fix |
|------|----------|--------|---------|-----|
| **COMPLETE_001** | 🟡 MEDIUM | −5 | Deductible not found | Verify deductible is listed |
| **COMPLETE_004** | 🔴 HIGH | −5 | Insurance company missing | Verify insurance company name |
| **COMPLETE_005** | 🟡 MEDIUM | −3 | License plate missing | Verify license plate present |
| **COMPLETE_006** | 🟡 MEDIUM | −2 | Odometer missing | Verify odometer reading |
| **COMPLETE_007** | 🔴 HIGH | −25* | Shop info missing (see supplement rules) | Provide shop name/address or Shop of Choice |
| **COMPLETE_008** | 🔴 HIGH | −25* | Shop of Choice on supplement | Replace with actual facility name + address |
| **COMPLETE_009** | 🔴 HIGH | — | Full 17-char VIN not recorded | Complete VIN required on every estimate |
| **COMPLETE_010** | 🟡 MEDIUM | — | Year/make/model incomplete | Complete vehicle identification required |

\* **Auto-Reject trigger**

### Supplement vs Original — Shop Rules

| Rule | Original | Supplement |
|------|----------|------------|
| COMPLETE_007 | Shop name OR Shop of Choice required | Full name + address required |
| COMPLETE_008 | N/A (Shop of Choice OK) | Shop of Choice → **AUTO-REJECT** |

---

## STATE COMPLIANCE RULES

| Rule | Severity | Points | Trigger | Fix |
|------|----------|--------|---------|-----|
| **STATEQC_001** | 🔴 HIGH | −8 | State not on estimate | Verify state in vehicle/insured section |
| **STATEQC_003** | ⛔ CRITICAL | −9 | TX estimate ≥ 80% of ACV | Flag for total loss review |

---

## EXCEPTION VERIFICATION RULES

| Rule | Severity | Points | Trigger | Suppressed On |
|------|----------|--------|---------|---------------|
| **EXCEP_001** | 🟡 MEDIUM | −3 | Supplement flags (`**`, S01/S02) | Supplements |
| **EXCEP_002** | 🟡 MEDIUM | −3 | Manual entries (`#` flag) | Supplements |
| **EXCEP_003** | 🟡 MEDIUM | −8 | A/M or AF parts | Never |

---

## LINE ITEM ANALYSIS RULES 🆕

### LINE_001 — Overlapping Operations
| Severity | 🟡 MEDIUM | **Points** | −8 |
|----------|-----------|------------|-----|
| **Trigger** | Same panel has same operation more than once |
| **Finding** | Potential overlapping operations: N line(s) |
| **Fix** | Review duplicate entries — remove or document justification |

### LINE_002 — Suspicious Labor Hours
| Severity | 🟢 LOW | **Points** | −3 |
|----------|--------|------------|-----|
| **Trigger** | Labor hours < 50% of expected minimum for the panel |
| **Minimums** | Hood ≥2h, Door ≥2h, Quarter ≥3h, Roof ≥4h, Bumper ≥1.5h |
| **Fix** | Verify labor hours are correct for the listed operation |

### LINE_003 — Missing Blend Panel
| Severity | 🟢 LOW | **Points** | −3 |
|----------|--------|------------|-----|
| **Trigger** | Painted panel has adjacent panel present in estimate but not painted |
| **Adjacent pairs** | hood→fender, fender→door, door→quarter, quarter→roof, bumper→hood, etc. |
| **Fix** | Check adjacent panel for required blend/clear coat |

### LINE_004 — LKQ Parts Notation
| Severity | 🟢 LOW | **Points** | −2 |
|----------|--------|------------|-----|
| **Trigger** | LKQ/USED/REC/REM part types present |
| **Fix** | Document LKQ part mileage, age, and warranty terms |

---

## FINANCIAL ANALYSIS RULES 🆕

### FIN_001 — Paint Materials Check
| Severity | 🟡 MEDIUM | **Points** | −5 |
|----------|-----------|------------|-----|
| **Trigger** | Paint labor hours present but no paint material line item |
| **Fix** | Add paint material line item (typically 30-35% of paint labor) |

### FIN_002 — Estimate vs ACV
| Severity | 🔴 HIGH (≥90%) / 🟡 MEDIUM (≥75%) | **Points** | −12 / −5 |
|----------|-------------------------------------|------------|-----------|
| **Trigger** | Estimate total ≥ 75% of ACV |
| **Fix** | ≥90%: Flag for total loss evaluation. ≥75%: Monitor for supplement creep |

---

## RATE VERIFICATION

| Rule | Severity | Trigger | Fix |
|------|----------|---------|-----|
| **TAX_001** | 🔴 HIGH | Tax rate differs >0.5% from reference | Verify correct rate for state/ZIP |
| **LABOR_001** | 🔴 HIGH | Labor rate >15% above prevailing | Verify rate for state/ZIP |

---

## SCORING MODEL

| Score | Status | Auditor Note |
|-------|--------|-------------|
| **128–150** | ✅ Pass | All checks passed. Estimate is complete and compliant. |
| **105–127** | ⚠️ Conditional | Conditional pass. Minor exceptions: review flagged items. |
| **0–104** | ❌ Fail | Not ready. Critical issues must be corrected before resubmission. |

**Auto-reject triggers (instant fail):**
- VIN photo missing (PHOTOCOV_001)
- Odometer photo missing (PHOTOCOV_002)
- Damage photos missing (PHOTOCOV_003)
- Shop info missing on supplement (COMPLETE_007, supplement)
- Shop of Choice on supplement (COMPLETE_008)
- Shop info missing on original (COMPLETE_007, original)

---

## REFERENCE DATA QUICK LOOKUP

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

*Rules: `src/rules/qc_rules.py` · Scorer: `src/rules/qc_scorer.py` · Reference: `src/rules/reference_data.py`*
