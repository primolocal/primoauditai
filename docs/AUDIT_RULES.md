# PrimoAuditAI — Unified Audit Ruleset (QC + Audit)

**Version:** v6.0 Final | **Rules:** 100+ | **Scoring:** 225 pts | **Pass:** 158 | **Categories:** 10

---

## 1. PHOTO COVERAGE (25 pts)

| Rule | Sev | Pts | Auto-Reject | Trigger |
|------|-----|-----|:---:|---------|
| PHOTOCOV_001 | HIGH | −25 | ✓ | VIN photo missing |
| PHOTOCOV_002 | HIGH | −25 | ✓ | Odometer photo missing |
| PHOTOCOV_003 | HIGH | −25 | ✓ | Replace ops but no damage photos |
| PHOTOCOV_004 | LOW | — | — | No body ops found with damage photos |
| PHOTOCOV_005 | MED | −5 | — | License plate photo not detected |
| PHOTOCOV_006 | MED | −5 | — | Photo count below panel count |
| PHOTOCOV_007 | LOW | −3 | — | No overview/full-vehicle photo |

---

## 2. ESTIMATE COMPLETENESS (25 pts)

| Rule | Sev | Pts | Auto-Reject | Trigger |
|------|-----|-----|:---:|---------|
| COMPLETE_001 | MED | −5 | — | Deductible missing |
| COMPLETE_004 | HIGH | −5 | — | Insurance company missing |
| COMPLETE_005 | MED | −3 | — | License plate missing |
| COMPLETE_006 | MED | −2 | — | Odometer missing |
| COMPLETE_007 | HIGH | −25 | ✓ | Shop info missing |
| COMPLETE_008 | HIGH | −25 | ✓ | Shop of Choice on supplement |
| COMPLETE_009 | HIGH | — | — | VIN not 17 characters |
| COMPLETE_010 | MED | — | — | Year/make/model incomplete |
| COMPL_011 | MED | — | — | Point of impact not recorded |
| COMPL_012 | LOW | — | — | Prior damage section empty |
| COMPL_013 | LOW | — | — | Production date not on estimate |
| CHECK_004 | LOW | — | — | Production date needed for parts compatibility |

### Supplement vs Original — Shop Rules

| | Original | Supplement |
|---|----------|------------|
| Shop info | Name OR Shop of Choice OK | Full name + address required |
| Shop of Choice | Allowed | **AUTO-REJECT** |

---

## 3. STATE COMPLIANCE (25 pts)

| Rule | State | Sev | Trigger |
|------|-------|-----|---------|
| STATEQC_001 | Any | HIGH | State not indicated |
| STATEQC_003 | TX | CRIT | Estimate ≥ 80% of ACV |
| STATEQC_010 | RI | CRIT | Non-OE part on vehicle < 30 months |
| STATEQC_011 | MN | MED | Non-OE parts without written disclosure |
| STATEQC_012 | WV | CRIT | A/M structural part on vehicle < 3 years |

---

## 4. EXCEPTION HANDLING (25 pts)

| Rule | Sev | Pts | Suppressed On | Trigger |
|------|-----|-----|---------------|---------|
| EXCEP_001 | MED | −3 | Supplements | Supplement flags (`**`, S01/S02) |
| EXCEP_002 | MED | −3 | Supplements | Manual entries (`#` flag) |
| EXCEP_003 | MED | −8 | Never | A/M or AF parts |
| EXCEP_004 | LOW | — | Never | Supplement count > 3 |
| EXCEP_005 | LOW | −2 | — | Multiple flag types on same line |

---

## 5. LINE ITEM ANALYSIS (25 pts)

| Rule | Sev | Pts | Trigger |
|------|-----|-----|---------|
| LINE_001 | MED | −8 | Same panel + operation duplicates |
| LINE_002 | LOW | −3 | Labor hours < 50% of expected minimum |
| LINE_003 | LOW | −3 | Painted panel missing blend on adjacent |
| LINE_004 | LOW | −2 | LKQ/USED parts without age/warranty notation |
| LINE_005 | MED | −5 | A/M parts without CAPA certification |

---

## 6. FINANCIAL ANALYSIS (25 pts)

| Rule | Sev | Pts | Trigger |
|------|-----|-----|---------|
| FIN_001 | MED | −5 | Paint labor but no materials line |
| FIN_002 | HIGH/MED | −12/−5 | Estimate ≥ 90%/75% of ACV |
| FIN_003 | MED | −5 | Paint materials > 38% of paint labor |
| FIN_004 | LOW | −3 | Sublet operations without invoice |
| MARKUP_001 | MED | −3 | Part price above expected range — verify |

---

## 7. PARTS SOURCING (25 pts)

| Rule | Sev | Pts | Auto-Reject | Trigger |
|------|-----|-----|:---:|---------|
| PART_001 | CRIT | −25 | ✓ | A/M part on structural/safety component |
| PART_002 | MED | −3 | — | High-value OE parts (>$2,000) |
| PART_003 | LOW | −2 | — | LKQ/used parts without warranty notation |
| AUDIT_009 | LOW | −2 | — | Part number but $0.00 price |
| NATGEN_015 | HIGH | −10 | ✓ | LKQ suspension parts prohibited |

---

## 8. LABOR ANALYSIS (25 pts)

| Rule | Sev | Pts | Auto-Reject | Trigger |
|------|-----|-----|:---:|---------|
| LABOR_001 | MED | −5 | — | Paint hours > 3× body hours |
| LABOR_002 | HIGH | −12 | ✓ | Zero labor hours on Replace line |
| LABOR_003 | LOW | −3 | — | Unitemized/miscellaneous charges |
| FRAME_001 | HIGH | — | — | Frame damage without set-up & measure |
| ALIGN_001 | HIGH | — | — | Tire/wheel damage without alignment |
| SUSP_001 | HIGH | −5 | — | Suspension work — alignment required |
| AUDIT_007 | HIGH | −12 | ✓ | Unexplained negative labor |
| AUDIT_008 | HIGH | −8 | — | Labor dollar amount without hours |
| AUDIT_010 | MED | −3 | — | Mechanical labor on cosmetic estimate |

---

## 9. CARRIER COMPLIANCE (25 pts)

| Rule | Sev | Pts | Auto-Reject | Source | Trigger |
|------|-----|-----|:---:|--------|---------|
| NATGEN_001 | HIGH | −8 | — | NatGen | Scan labor > 0.5 hours |
| NATGEN_002 | HIGH | −8 | — | NatGen | Calibration on original — defer to supplement |
| NATGEN_004 | HIGH | −10 | — | NatGen | OEM part — requires current MY + <15K mi |
| NATGEN_006 | MED | −5 | — | NatGen | Unjustified Replace on common panels |
| NATGEN_007 | MED | −3 | — | NatGen | Unnecessary blend |
| NATGEN_008 | LOW | −2 | — | NatGen | Cosmetic R&I — verify repair access |
| NATGEN_010 | HIGH | −8 | — | NatGen | Sublet charge requires invoice |
| NATGEN_012 | HIGH | −5 | — | NatGen | Large paint scope (≥3 refinish panels) |
| NATGEN_013 | HIGH | −10 | ✓ | NatGen | Body shop supplies — NEVER allowed |
| NATGEN_014 | HIGH | −10 | ✓ | NatGen | Flex additive — NEVER allowed |
| NATGEN_015 | HIGH | −10 | ✓ | NatGen | LKQ suspension parts prohibited |
| NATGEN_016 | CRIT | −25 | ✓ | NatGen | A/M safety system part — LKQ/OEM only |
| NATGEN_020 | MED | −3 | — | NatGen | Haz waste exceeds $5.00 cap |
| NATGEN_022 | MED | −3 | — | NatGen | Total loss — write 100% of damages |
| COVER_001 | HIGH | −5 | — | Tommy | Cover car missing with refinish |
| DAMVAL_001 | HIGH | −8 | — | Tommy | Damage-to-value % not in notes (>$3K) |
| ESCALATE_001 | HIGH/MED | −10/−5 | — | Tommy | $10K+ estimate — escalation recommended |
| MOTOR_001 | MED | −3 | — | MOTOR | R&I included in parent operation |
| SUPP_002 | HIGH | −8 | — | Supp | Calibration — invoice required |
| SUPP_003 | HIGH | −8 | — | Supp | Scan charge — invoice/scan report required |
| SUPP_004 | HIGH | −8 | — | Supp | Wheel alignment — invoice required |
| SUPP_005 | HIGH | −8 | — | Supp | Sublet on supplement — invoice required |
| CHECK_001 | HIGH | −8 | — | Audit | NADA valuation required (>$5K) |
| GLASS_001 | HIGH | −5 | — | New | Windshield replaced — ADAS calibration? |
| BUMPER_001 | MED | −3 | — | New | Bumper cover replaced — absorber check |
| EMBLEM_001 | LOW | −2 | — | New | Emblem R&I included in panel replacement |
| HAIL_002 | HIGH | −8 | — | Hail | Windshield on hail claim — verify causation |

---

## 10. RATE VERIFICATION (deductions)

| Rule | Sev | Trigger |
|------|-----|---------|
| TAX_001 | HIGH | Tax rate differs >0.5% from reference |
| LABOR_001 | HIGH | Labor rate >15% above prevailing |

---

## SCORING MODEL

| Score | Status |
|-------|--------|
| **191–225** | ✅ Clean pass — ready for carrier |
| **158–190** | ⚠️ Conditional pass — minor exceptions |
| **0–157** | ❌ Not ready — critical issues |

### Auto-Reject Triggers (12)
1. VIN photo missing (PHOTOCOV_001)
2. Odometer photo missing (PHOTOCOV_002)
3. Damage photos missing with Replace ops (PHOTOCOV_003)
4. Shop info missing (COMPLETE_007)
5. Shop of Choice on supplement (COMPLETE_008)
6. A/M structural parts (PART_001)
7. Zero labor on Replace (LABOR_002)
8. Unexplained negative labor (AUDIT_007)
9. A/M safety system parts (NATGEN_016)
10. Body shop supplies (NATGEN_013)
11. Flex additive (NATGEN_014)
12. LKQ suspension parts (NATGEN_015)

---

## STATE-SPECIFIC RULES

| State | Rule | Requirement |
|-------|------|-------------|
| TX | STATEQC_003 | Total loss threshold at 80% of ACV |
| RI | STATEQC_010 | OE parts required on vehicles < 30 months |
| MN | STATEQC_011 | Written disclosure required for non-OE parts |
| WV | STATEQC_012 | OE required for structural parts on vehicles < 3 years |

---

## SUPPLEMENT vs ORIGINAL

| Rule | Original | Supplement |
|------|----------|------------|
| COMPLETE_007 | Shop OR Shop of Choice | Full name + address |
| COMPLETE_008 | OK | AUTO-REJECT |
| EXCEP_001/002 | Active | Suppressed |
| NATGEN_002 | Defer to supplement | Invoice required |
| SUPP_002-005 | N/A | Invoice required |

---

## MOTOR P-PAGE INCLUDED OPERATIONS

When a **parent** operation exists, **child** R&I is included per MOTOR:

| Parent | Child R&I Included |
|--------|-------------------|
| Hood | Insulator, hinge |
| Door | Belt molding, weatherstrip, mirror, handle, lock, latch, regulator, trim panel, glass, run channel |
| Bumper | Bracket, reinforcement, absorber, impact bar |
| Fender | Liner, splash shield |
| Roof | Headliner, sunroof, roof rack, antenna |
| Liftgate | Trim panel, glass, wiper, handle, molding, emblem, nameplate |
| Quarter | Trim panel, glass, molding |
| Headlamp | Bracket, mounting panel |
| Deck lid | Trim panel, lock, emblem, nameplate, spoiler |
| Radiator | Condenser, fan |
| Frame | Crossmember, body mount |

---

## ENDPOINTS

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/qc` | Upload estimate + image PDF, run all 100+ rules |
| POST | `/api/audits` | Upload estimate PDF, run unified ruleset |
| GET | `/api/qc` | List QC packets |
| GET | `/api/qc/{id}` | Packet detail with findings + photos |
| GET | `/api/audits` | List audits |
| GET | `/api/audits/{id}` | Audit detail with findings |
| PATCH | `/api/qc/{id}/photos/{photo_id}/type` | Override photo type |
| PATCH | `/api/qc/{id}/photos/{photo_id}/location` | Override location |
| DELETE | `/api/qc/{id}/photos/{photo_id}` | Remove photo |
| GET | `/api/dataset/export` | Export training data |
| GET | `/api/vision/status` | Active detector type |

---

*Source: `backend/src/rules/qc_rules.py` · `backend/src/rules/qc_scorer.py` · `backend/src/rules/reference_data.py` · `backend/src/api/routes/audit.py`*
