# PrimoAuditAI — QC Audit Rules Reference

**Version:** v2 | **Generated:** June 9, 2026 | **Source:** `backend/src/rules/qc_rules.py`

---

## Overview

PrimoAuditAI evaluates every estimate + photo packet against **14 rules** across **4 categories**, plus **2 rate verification checks**. Each rule produces a finding with severity, description, and suggested fix.

**Scoring model:** 100 points total (25 per category). Pass threshold: **70/100**.

---

## Rule Categories

| Category | Rule IDs | Points | Description |
|----------|----------|--------|-------------|
| **Photo Coverage** | PHOTOCOV_001–004 | 25 | VIN, odometer, and damage photos present |
| **Estimate Completeness** | COMPLETE_001–008 | 25 | Deductible, shop info, insurance, odometer, license |
| **State Compliance** | STATEQC_001–003 | 25 | State present, TX total loss threshold |
| **Exception Verification** | EXCEP_001–003 | 25 | Supplement flags, manual entries, A/M parts |
| **Rate Verification** | TAX_001, LABOR_001 | Deductions | Tax rate and labor rate against reference |

---

## PHOTO COVERAGE RULES

### PHOTOCOV_001 — VIN Missing
| Field | Value |
|-------|-------|
| **Severity** | 🔴 HIGH |
| **Auto-Reject** | YES (−25 pts) |
| **Trigger** | No VIN checkbox AND no photo classified as `vin` |
| **Finding** | VIN photo required but not found in packet |
| **Fix** | Upload VIN plate photo |

### PHOTOCOV_002 — Odometer Missing
| Field | Value |
|-------|-------|
| **Severity** | 🔴 HIGH |
| **Auto-Reject** | YES (−25 pts) |
| **Trigger** | No odometer checkbox AND no photo classified as `odometer` |
| **Finding** | Odometer/mileage photo required but not found |
| **Fix** | Upload dashboard photo showing mileage |

### PHOTOCOV_003 — Damage Photos Missing
| Field | Value |
|-------|-------|
| **Severity** | 🔴 HIGH |
| **Auto-Reject** | YES (−25 pts) |
| **Trigger** | Replace operations found on estimate, but no damage photos uploaded |
| **Finding** | Replace operations found (N panels) but no damage photos |
| **Fix** | Upload photos of damaged panels listed in estimate |

### PHOTOCOV_004 — No Panel Operations Found
| Field | Value |
|-------|-------|
| **Severity** | 🟢 LOW |
| **Trigger** | Damage photos present but no body/paint operations (Rpr, R&I, Repl) found |
| **Finding** | No body/paint operations found — verify damage photos show all impact areas |

---

## ESTIMATE COMPLETENESS RULES

### COMPLETE_001 — Deductible Missing
| Field | Value |
|-------|-------|
| **Severity** | 🟡 MEDIUM |
| **Points** | −5 |
| **Trigger** | Deductible not found on estimate |
| **Fix** | Verify deductible is listed on estimate or in notes |

### COMPLETE_004 — Insurance Missing
| Field | Value |
|-------|-------|
| **Severity** | 🔴 HIGH |
| **Points** | −5 |
| **Trigger** | Insurance company/carrier not listed |
| **Fix** | Verify insurance company name is present |

### COMPLETE_005 — License Plate Missing
| Field | Value |
|-------|-------|
| **Severity** | 🟡 MEDIUM |
| **Points** | −3 |
| **Trigger** | License plate not recorded on estimate |
| **Fix** | Verify license plate is present in vehicle section |

### COMPLETE_006 — Odometer Missing
| Field | Value |
|-------|-------|
| **Severity** | 🟡 MEDIUM |
| **Points** | −2 |
| **Trigger** | Odometer not recorded on estimate |
| **Fix** | Verify odometer reading is present |

### COMPLETE_007 — Shop Info Missing
| Field | Value |
|-------|-------|
| **Severity** | 🔴 HIGH |
| **Auto-Reject** | YES (−25 pts) |
| **Trigger (Original)** | No shop name AND no Shop of Choice |
| **Trigger (Supplement)** | Shop name OR address missing |
| **Fix (Original)** | Repair facility must be identified, or Shop of Choice designated |
| **Fix (Supplement)** | Repair facility with name and address must be listed on all supplements |

### COMPLETE_008 — Shop of Choice on Supplement
| Field | Value |
|-------|-------|
| **Severity** | 🔴 HIGH |
| **Auto-Reject** | YES (−25 pts) |
| **Trigger** | Supplement uses "Shop of Choice" instead of actual shop info |
| **Fix** | Replace Shop of Choice with actual repair facility name and address |
| **Note** | Supplements are stricter than originals — full shop info required |

---

## STATE COMPLIANCE RULES

### STATEQC_001 — State Missing
| Field | Value |
|-------|-------|
| **Severity** | 🔴 HIGH |
| **Points** | −8 |
| **Trigger** | State not indicated on estimate |
| **Fix** | Verify state is present in vehicle/insured section |

### STATEQC_003 — TX Total Loss Threshold (80%)
| Field | Value |
|-------|-------|
| **Severity** | ⛔ CRITICAL |
| **Points** | −9 |
| **Trigger** | TX estimate total ≥ 80% of ACV |
| **Fix** | Flag for total loss review or obtain NADA valuation |
| **Formula** | `total / ACV ≥ 0.80` |

---

## EXCEPTION VERIFICATION RULES

### EXCEP_001 — Supplement Flags
| Field | Value |
|-------|-------|
| **Severity** | 🟡 MEDIUM |
| **Points** | −3 |
| **Trigger** | Lines with `**` flag or supplement markers (S01/S02) |
| **Fix** | Ensure prior supplement documentation is attached |
| **Suppressed on** | Supplements (flags are expected on supps) |

### EXCEP_002 — Manual Entries (#)
| Field | Value |
|-------|-------|
| **Severity** | 🟡 MEDIUM |
| **Points** | −3 |
| **Trigger** | Lines with `#` flag (manual part entry) |
| **Fix** | Ensure justification is documented for each manual entry |
| **Suppressed on** | Supplements |

### EXCEP_003 — Aftermarket (A/M) Parts
| Field | Value |
|-------|-------|
| **Severity** | 🟡 MEDIUM |
| **Points** | −8 |
| **Trigger** | Lines with `part_type` = `A/M` or `AF` |
| **Fix** | Verify shop provided justification for aftermarket part selection |
| **Applies to** | Both originals and supplements |

---

## RATE VERIFICATION

### TAX_001 — Tax Rate Mismatch
| Field | Value |
|-------|-------|
| **Severity** | 🔴 HIGH |
| **Trigger** | Estimate tax rate differs from reference by >0.5% |
| **Reference** | Tax Foundation 2024 state + local combined rates |
| **Fix** | Verify correct tax rate for [STATE] ZIP [ZIP]. Expected: X% |

### LABOR_001 — Labor Rate Exceeds Prevailing
| Field | Value |
|-------|-------|
| **Severity** | 🔴 HIGH |
| **Trigger** | Estimate labor rate >15% above prevailing rate for state/ZIP |
| **Reference** | CCC/Mitchell prevailing body labor rates by state/ZIP |
| **Fix** | Verify labor rate for [STATE] ZIP [ZIP]. Upper limit: $X/hr |

---

## SCORING MODEL

| Score Range | Status | Auditor Note |
|-------------|--------|-------------|
| **85–100** | ✅ Pass | All checks passed. Estimate is complete and compliant. |
| **70–84** | ⚠️ Conditional | Conditional pass. Minor exceptions: review flagged items. |
| **0–69** | ❌ Fail | Not ready. Critical issues must be corrected before resubmission. |

**Auto-reject triggers (instant fail regardless of score):**
- VIN photo missing (PHOTOCOV_001)
- Odometer photo missing (PHOTOCOV_002)
- Damage photos missing (PHOTOCOV_003)
- Shop info missing on supplement (COMPLETE_007, supplement mode)
- Shop of Choice on supplement (COMPLETE_008)
- Shop info missing on original (COMPLETE_007, original mode)

---

## SUPPLEMENT vs ORIGINAL DIFFERENCES

| Rule | Original | Supplement |
|------|----------|------------|
| COMPLETE_007 | Shop info OR Shop of Choice required | Full name + address required |
| COMPLETE_008 | N/A (Shop of Choice is OK) | Shop of Choice → AUTO-REJECT |
| EXCEP_001 | Supplement flags trigger | **Suppressed** (flags expected) |
| EXCEP_002 | Manual entries trigger | **Suppressed** |
| EXCEP_003 | A/M parts trigger | A/M parts trigger (same) |

---

## REFERENCE DATA

### Labor Rates (prevailing, by state)
Source: CCC/Mitchell 2024 surveys. Default state averages:
- TX: $62/hr (Dallas $70, Houston $72, Austin $68, San Antonio $65)
- CA: $78/hr (LA $82, SF $85, SD $80)
- NY: $78/hr (NYC $85, Buffalo $72)
- FL: $62/hr

### Tax Rates (state + local combined)
Source: Tax Foundation 2024:
- TX: 8.25%
- CA: 8.85% (LA 10.25%)
- NY: 8.52% (NYC 8.875%)
- FL: 7.02%
- DE, MT, NH, OR: 0% (no sales tax)

---

## API ENDPOINTS

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/qc` | Upload estimate + image PDF, run all rules |
| GET | `/api/qc` | List all QC packets |
| GET | `/api/qc/{id}` | Get packet detail with findings + photos |
| PATCH | `/api/qc/{id}/photos/{photo_id}/type` | Override photo classification |
| PATCH | `/api/qc/{id}/photos/{photo_id}/location` | Override damage location |
| DELETE | `/api/qc/{id}/photos/{photo_id}` | Remove photo from packet |
| GET | `/api/dataset/export` | Export training data |
| GET | `/api/vision/status` | Diagnostic: active detector type |

---

*Rules engine: `backend/src/rules/qc_rules.py` · Scorer: `backend/src/rules/qc_scorer.py` · Reference data: `backend/src/rules/reference_data.py`*
