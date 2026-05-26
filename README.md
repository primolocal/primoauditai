# PrimoAuditAI

PrimoAuditAI is a machine learning powered automotive claims auditing platform. By combining a deterministic Carrier Compliance parsing engine with the PrimoAudit Intelligence suggestion layer, it actively analyzes carrier EMS estimates against industry guidelines to reduce uncaptured exceptions and expedite manual auditor workflows.

## System Architecture Overview
The platform enforces a strict separation between strict, hard-coded carrier compliance rules (The Substrate) and the cognitive suggestion layer powered by the LLM Agents (PrimoAudit Intelligence).

### LLM Provider Support
PrimoAuditAI supports multiple Hermes intelligence backends, selectable via `HERMES_PROVIDER` env:

| Provider | Type | Model | Latency | Best For |
|----------|------|-------|---------|----------|
| `simulator` | Mock | N/A | Instant | Development, unit tests |
| `google_genai` | Managed | Gemini 2.5 Flash | ~2s | Production, general reasoning |
| `ollama_cloud` | **Recommended** | kimi-k2.6:cloud / glm-5.1:cloud | ~3-5s | **Your existing sub** — best cost/quality ratio for your stack |
| `remote_hermes` | VPS | Custom | ~1-4s | Self-hosted, air-gapped |

### Key Components:
- **FastAPI / Python Compliance Backend**: Standardized rules engine. SQLite/PostgreSQL persistence.
- **Next.js / TypeScript Web App**: The frontend Analyst Workstation, optimized for lightning-fast determinations.
- **Object Storage Service**: Pluggable storage system mapping zip asset extractions to Local Volume / S3 buckets.

## Ollama Cloud Setup
If you're already subscribed to Ollama Cloud Pro ($20/mo), PrimoAuditAI can use your existing API key directly — no new subscriptions needed.

```bash
# backend/.env
HERMES_PROVIDER=ollama_cloud
OLLAMA_CLOUD_API_KEY=ocp_your_key_here   # https://ollama.com/settings/cloud
OLLAMA_CLOUD_MODEL=kimi-k2.6:cloud
OLLAMA_CLOUD_VISION_MODEL=glm-5.1:cloud
OLLAMA_CLOUD_TIMEOUT=45.0
OLLAMA_CLOUD_TEMPERATURE=0.2
```

For vision analysis, `glm-5.1:cloud` is used for photo evidence review. For text reasoning, `kimi-k2.6:cloud` powers the audit intelligence layer. Both are your existing models.

## Local Testing
From the root of the repository, execute the included dev-scripts from `frontend/package.json` to spin up both layers concurrently. (Ensure your active python binary or venv is configured appropriately):
```bash
cd frontend
npm run dev:all
```
Your local system will start the FastAPI backend on `http://127.0.0.1:8000` and the React frontend on `http://localhost:3000`.

## Docker Production Mapping
To spin up a fully isolated environment including the managed Postgres container stack:
```bash
docker-compose up --build -d
```
All system configuration (Ports, Credentials, LLM Models, Output Storage Modes) is controlled dynamically via the attached `.env` variables list.
