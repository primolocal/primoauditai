# Audit Evaluation Pipeline

This outlines the precise execution sequence of a claim through the PrimoAuditAI platform from ingestion to report delivery.

## 1. Upload & Ingestion (Frontend)
- An auditor manually drops an EMS ZIP package (containing estimate data, assignment metadata, and subfolder asset structures) via the `UploadHarness`.
- Additional PDF invoices or supplemental photos are uploaded as necessary.
- **Action**: Frontend dispatches a `POST /api/audits` payload carrying the multipart boundary bytes.

## 2. Background Task Allocation (FastAPI)
- The backend instantly generates a unique `audit_id` and a `job_id`.
- The synchronous API request is decoupled; it returns `{"status": "processing"}` to unblock the frontend React interface.
- **Action**: Frontend loops into a 2s -> 5s exponential polling cycle on `GET /api/audits/{audit_id}/status`. FastAPI hooks the `pipeline_worker.py` onto an asynchronous queue.

## 3. Storage Abstraction & Intake Execution
- The `StorageProvider` interface persists the raw ZIP and assets to the designated cloud/local volume and creates database indices in `AssetRecordModel`.

## 4. Analytical Pipeline

### Stage A: EMS Parsing
- **Intake Agent** mounts the Zip and strips out unstructured estimate line items.
- Line items are normalized into standard formats representing Part, Operation, Price, Quantity, and Labor parameters.

### Stage B: Computer Vision (Photo Agent)
- Image/PDF bytes are shunted into the OCR pipeline via the `EvidenceParser`.
- Supporting elements (Sublet Invoices, Check Receipts, Damage Appraisals) are tagged and converted into structured relational anchors for the EMS lines.

### Stage C: Compliance Engine
- The combined Estimate and Evidence Matrices are fed into the Deterministic Rules Engine.
- The system executes structural pass/fail boolean logic across the data contract mapping.

### Stage D: PrimoAudit Intelligence Overlayer
- The `Audit Agent` extracts the failed findings payload.
- It forwards this array into the Hermes/Intelligence module, which uses generative models to construct natural language rationales, flag edge-case confidence, and formulate proactive revision recommendations without functionally mutating the underlying rule violations.

## 5. Persistence
- The final payload is bundled, scored into categories, and serialized as `JSONB` into the `AuditRun.summary_json` column within PostgreSQL.
- Processing job flags flip to `completed`.

## 6. Feedback Delivery (Report Agent)
- The React Frontend fires a terminal fetch grabbing the completed AuditRun payload.
- The workstation UI hydrater renders the "Scorecard" and "Narrative" modules.
- The auditor approves or overturns the Findings, closing the loop and triggering telemetry.
