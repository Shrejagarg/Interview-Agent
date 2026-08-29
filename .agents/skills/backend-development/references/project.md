# This Project — AI Interview Simulator (Backend)

Act as the backend engineer on **interview-agent** (git branch `phase1-backend-refactor`). Apply the skill's principles, but respect the project's existing choices below.

## Layout

```
backend/app/
  __init__.py     # FastAPI app factory, router mounting, startup warnings
  config.py       # os.getenv-based settings (no Pydantic Settings yet)
  db/
    database.py   # SQLAlchemy engine + SessionLocal
    models.py     # ORM models (User, Company, InterviewSession, Answer,
                  # Webhook, WebhookDelivery, ...)
  api/            # routers: auth, company, domains, interviews, analytics, webhooks
  domains/        # per-domain question/metadata: finance, hr, marketing, sales, software_engineering
  models/         # legacy Pydantic schemas
  services/       # orchestration helpers
  tests/          # pytest suite (TestClient + tmp SQLite)
```

There is also a shared `core/` **library** (engine, evaluator, resume_parser, question_engine, domains, analytics) imported by the API. It is a stable brain — **do not modify it unless there is a real defect**.

## Conventions that override the skill's generic defaults

- **Sync FastAPI functions** (plain `def`, not `async def`). No `async def` endpoints, no Celery. Background webhook dispatch uses `BackgroundTasks`.
- **SQLAlchemy** with a SQLite default (`DATABASE_URL` unset → `sqlite:///./interview.db`; set `DATABASE_URL=postgresql://...` for Postgres). Tables created via `Base.metadata.create_all()` from `app.db.models` import.
- **Testing**: `pytest` with `TestClient`, no Ruff/MyPy/structlog/testcontainers yet — match existing style. `python -m pytest -q` from `backend/` (124 tests) or from repo root (289 total, includes legacy `tests/test_api.py`).
- **Auth**: JWT (HS256, `JWT_SECRET_KEY`, `ACCESS_TOKEN_EXPIRE_MINUTES`, 7-day default) + bcrypt via `passlib` (`pwd_context`, `bcrypt==4.0.1` pinned). Passwords >72 bytes are SHA-256 pre-hashed before bcrypt. Dev-mode token bypass exists for local testing.
- **Secrets**: `DEFAULT_JWT_SECRET` is a dev fallback; never ship it in prod config.

## Key domain facts

- Scores are **0–10** (GEMINI Flash evaluation in `core/evaluator.py`, ollama fallback). Verdict thresholds from `core/config.py`: **7 = Strong, 5 = Average**.
- Webhooks: `POST/GET/PUT/DELETE /api/webhooks`, `POST /{id}/test`, `GET /{id}/deliveries`. HMAC-SHA256 signature header `X-Webhook-Signature: sha256=...`. Public URLs must be HTTPS; loopback/private/reserved IPs blocked (SSRF) unless `ENV=development` or `WEBHOOK_ALLOW_PRIVATE=1`. Retries 1s→2s→4s, `WEBHOOK_MAX_RETRIES=3`, `WEBHOOK_TIMEOUT_SECONDS=10`.
- Config env names live in `backend/app/config.py` (WEBHOOK_*, JWT_*, CORS_ORIGINS, ENV, OLLAMA_HOST, MODEL_NAME).

## Golden rules

1. Every feature ships with its tests (`backend/tests/`).
2. Keep changes minimal and in existing style; prefer plain, readable code.
3. Never expose webhook secrets — returned only in the create response.
4. Reuse `core/` as a library; raise defects to the team instead of silently patching.
5. Run the full suite from repo root before finishing: `python -m pytest -q` → 289 passed.