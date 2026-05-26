# PrimoAuditAI Architecture

PrimoAuditAI is an advanced auditing platform that fuses deterministic rules-based evaluation with specialized AI agents to streamline the review of automotive collision claims.

## System Layers

The system is constructed with strict structural boundaries separating deterministic logic from probabilistic intelligence:

### 1. Deterministic Rules Engine (The Substrate)
This layer acts as the absolute source of truth. It executes hard-coded structural validations to check EMS line items against standard collision estimating protocols, local regulations, and carrier-specific compliance matrices. The Rules Engine strictly dictates what constitutes a "Finding" (an exception to established rules).

### 2. PrimoAudit Intelligence (The Suggestion Layer)
Formerly referred to as Hermes, this cognitive reasoning layer sits conceptually above the Deterministic Engine. It does *not* directly alter claim math or structural verdicts. Instead, it reads the outputs of the rules engine, digests evidence assets (photos/invoices), and injects context-aware recommendations, critique confidence scores, and action rationale for the human auditor. It serves purely in an advisory capacity.

### 3. The Learning System
The recursive feedback mechanism capturing how human auditors interact with the PrimoAudit Intelligence suggestions. By tracking confirmations, overturns, and dismissals, the learning system identifies "Rule Drift" over time and proposes iterative adjustments back to the Rules Engine.

---

## SOUL Agents Hierarchy

The PrimoAudit Intelligence layer is orchestrated by distinct, purpose-built SOUL (Systemic Operation & Understanding Logic) Agents.

### Intake Agent
Responsible for interpreting incoming raw claim packages (EMS + PDF + Photos). It unpacks ZIP payloads, runs NLP over estimator notes, tags unstructured parts data, and prepares a standardized metadata payload for downstream evaluation.

### Photo Agent
The computer vision parser. It identifies photo context, matches damage images line-by-line with estimator billing logic, and extracts OCR text (e.g. from sublet invoices) to append to the Evidence Matrix.

### Audit Agent
The core orchestration agent that processes the combined data (Intake payload + Photo mapping) through both the Deterministic Rules Engine and the PrimoAudit Intelligence critique logic. It surfaces final "Findings".

### Report Agent
Translates raw JSON exception outputs into the frontend-consumable state payloads. It powers the Scorecard generation, creates human-readable audit narratives, and prepares email directives for outward carrier communication.

### Feedback Agent
The telemetry processor running asynchronously. It hooks into the auditor's workstation event stream, monitors final approval verdicts on Findings versus initially detected confidence intervals, and drives the telemetry metrics powering the Learning System.

---

## High-Level System Diagram

```
[ Frontend: React/Next.js ]
         │
         ▼
[ Intake Agent ] ──────────┐
         │                 │
         ▼                 ▼
[ Photo Agent ] ────> [ Audit Agent ]
                           │
      ┌────────────────────┼────────────────────┐
      ▼                    ▼                    ▼
[ Deterministic ]  [ PrimoAudit       ]  [ Learning    ]
[ Rules Engine  ]  [ Intelligence     ]  [ System      ]
      │                    │                    │
      └────────────────────┼────────────────────┘
                           ▼
                   [ Report Agent ]
                           │
                           ▼
               [ Outbound Carrier Email ]
```
