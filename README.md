# PrimoAuditAI v2

AI-powered auto damage estimate auditing for professional insurance appraisers.

## Architecture

Decoupled FastAPI backend + Next.js 14 frontend. Domain-driven rules engine with 53+ audit rules across 7 categories.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI 0.110+ · Python 3.11+ · Pydantic v2 |
| Frontend | Next.js 14 (App Router) · React 18 · TypeScript 5.3+ |
| Database | PostgreSQL 16 · SQLAlchemy 2.0 · asyncpg |
| Testing | pytest 8 · pytest-asyncio · Vitest · Playwright |
| Vision | qwen3-vl:235b via Ollama Cloud |
| Deployment | Railway (backend/DB) · Vercel (frontend) |

## Development

```bash
# Start PostgreSQL + backend + frontend
docker compose up -d

# Backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn src.api.app:app --reload --host 0.0.0.0 --port 8000

# Frontend
cd frontend
npm install
npm run dev
```

## License

MIT
# Mon Jun  8 09:12:19 CDT 2026
