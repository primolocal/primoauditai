# Learning System

The Learning System is the telemetry backbone of PrimoAuditAI. While the System Deterministic Rules are hardcoded (and act as a compliance baseline), the Learning System dynamically analyzes real-world exceptions over time based directly on Auditor disposition inputs.

## Core Objective
Its primary goal is anomaly detection and identifying "Rule Drift." It captures the difference between what the automated Intelligence layer flagged as an error and what the human expert auditor eventually decided to keep (or overturn) in production.

---

## Feedback Event Types

Every "Finding" triggered in a claim audit forces a human-in-the-loop validation step via the React Analyst Workstation. The emitted events include:

1. **`approve`** (Confirmed)
   - The estimator rule was legitimately violated. The AI correctly identified the discrepancy, and the auditor intends to penalize or revise the carrier invoice.
2. **`reject`** (Overturned)
   - The AI flagged a violation, but the auditor recognized contextual nuance (e.g., a specific sublet contract allowed this exact behavior) and dismissed the finding.
3. **`adjust`** (Modified)
   - The AI flagged a penalty, but the amount or rationale was manually edited by the auditor prior to outbound carrier delivery.
4. **`missed`** (Manual Findings)
   - The auditor manually appended a finding that the PrimoAudit Rules Engine failed to detect natively from the EMS stream.

---

## Signal Generation & Telemetry

When an event triggers, the React UI (`UploadHarness` -> `/api/audits/{audit_id}/findings/{finding_id}/{action}`) routes the metadata into the backend `ActionPayload` schema. It is serialized within `AuditRun.activity_log` and saved instantly.

As the dataset scales, the `Feedback Agent` periodically synthesizes these signals against active rule matrices to identify systemic issues across thousands of claims.

## Output Boundaries

The suggestions produced by the Learning System are fundamentally classified into distinct execution buckets:

### `auto_safe_updates`
- Internal mapping fixes (e.g., specific OEM terminology definitions that were not matching).
- Low risk string standardizations applied to the Intake Agent.

### `suggested_updates`
- Generative AI critique enhancements.
- "We noticed auditors reject this rule 80% of the time when Carrier X is involved. Consider adjusting the Guideline parameters for Carrier X."
- These updates are *always* reviewed by an administrator during a deployment stage.

### `locked_rule_conflicts`
- Situations where human behavior consistently violates a hard-coded regulatory or structural logic check.
- The Learning System highlights the disparity ("Auditors are consistently passing missing structural documentation on total-losses"), but does not overwrite the Deterministic Substrate under any circumstance. Humans must intervene manually to loosen the rule.
