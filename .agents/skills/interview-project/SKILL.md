---
name: interview-project
description: This repo's operating manual. Use this skill whenever you work inside the AI Interview Simulator project (interview-agent) — backend/FastAPI, frontend/Next.js, webhooks, resume parsing or LLM evaluation work, or anything under core/, backend/, frontend/, tests/, or .agents/skills/. It maps the codebase, enforces the golden rules (never touch core/ without a defect, all tests must pass), and routes work to the right specialized skill (backend-development, web-development, web-testing, webapp-testing, cybersecurity, frontend-design, pdf, docx, skill-creator, mcp-builder). Always load this skill first, then delegate to the specialized one.
---

This is the **AI Interview Simulator** (repo root `R:\IMP\interview v2`, git branch `phase1-backend-refactor`). Read this before making any change, then consult the specialized skill for the area being touched.

## Repo map

```
core/                      # Shared "brain" library: engine, interviewer,
                           # evaluator (Gemini Flash / ollama), resume_parser
                           # (pdfplumber, python-docx), question_engine, domains,
                           # analytics. STABLE — do not modify without a real defect.
backend/app/
  __init__.py              # FastAPI app factory, router mounting, JWT default warn/guard
  config.py                # os.getenv settings (JWT_*, WEBHOOK_*, ENV, OLLAMA_HOST, MODEL_NAME)
  db/database.py           # SQLAlchemy engine; DATABASE_URL default sqlite:///./interview.db
  db/models.py             # ORM models: User, Company, InterviewSession, Answer, Webhook, WebhookDelivery...
  api/                     # routers: auth, company, domains, interviews, analytics, webhooks
  domains/                 # per-domain data: finance, hr, marketing, sales, software_engineering
  models/                  # legacy Pydantic schemas
  services/                # orchestration helpers
  tests/                   # pytest suite (124 backend tests)
frontend/web/
  src/app/                 # Next.js 14 App Router: (auth), (candidate), (company) route groups
  package.json             # React 18, Next 14.2.35, Tailwind; no test framework yet
tests/test_api.py          # legacy root suite (part of the 289)
test_resumes/              # parser fixtures
traefik/                   # deployment ingress config (Docker-only, not local)
```

## Golden rules

1. **Never touch `core/`** unless there is a genuine defect. Prefer fixing in `backend/` or `frontend/`.
2. **All tests must pass** before finishing: run `python -m pytest -q` from the repo root (**289 passed**). Do not delete or weaken tests; add tests with every feature.
3. **Keep changes minimal and in existing style.** Match surrounding code; no new heavy deps without justification.
4. **Sync FastAPI** functions, SQLAlchemy (SQLite default), no Celery/async endpoints. Webhook dispatch uses `BackgroundTasks`.
5. **Secrets**: don't log or serialize them in responses; `DEFAULT_JWT_SECRET` is a dev-only fallback.
6. **Scores 0–10**; verdict thresholds from `core/config.py`: `strong_threshold=7`, `average_threshold=5`.
7. **Webhooks**: HMAC-SHA256 (`X-Webhook-Signature: sha256=...`), secret returned only on create, public URLs HTTPS-only, SSRF block for private/loopback IPs (unless `ENV=development`/`WEBHOOK_ALLOW_PRIVATE=1`), retries 1s→2s→4s.

## Which skill routes here

| Task | Skill |
|---|---|
| Backend API, FastAPI, SQLAlchemy, endpoints, backend tests | **backend-development** |
| Frontend features, Next.js structure | **web-development** |
| Frontend tests (Vitest/RTL — planned, not installed) | **web-testing** |
| Browser/E2E checks (Playwright — planned, not installed) | **webapp-testing** |
| Security review of changes (webhooks, auth, Docker) | **cybersecurity** |
| UI aesthetic direction | **frontend-design** |
| Resume PDF handling | **pdf** / **docx** |
| Authoring/modifying skills in this repo | **skill-creator** |
| Future MCP server integration | **mcp-builder** |

Each route: load the specialized skill, then **read its `references/project.md`** (e.g., `.agents/skills/backend-development/references/project.md`) for this repo's concrete conventions and surfaces.

## Workflow

1. Explore the relevant area (never guess file layout); read the skill's `references/project.md`.
2. Make the minimal change in existing style.
3. Add/update tests in the owning suite.
4. Run `python -m pytest -q` from repo root; confirm 289 passed (or the increased count).
5. Report concisely: what changed, test result, any follow-ups.