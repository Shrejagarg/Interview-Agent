# This Project — Threat Model & Security Review Surfaces

Apply the skill's principles to the concrete surfaces below. Review the checklist section of this skill before every feature merge.

## Auth & identity

- **JWT** HS256; dev fallback secret `DEFAULT_JWT_SECRET` in `backend/app/config.py` — must never appear in production config. `ENV=production` should hard-fail on the default secret.
- **bcrypt** (passlib, `bcrypt==4.0.1` pinned); passwords over 72 bytes are SHA-256 pre-hashed (both hash and verify paths must stay in lockstep).
- Dev-mode token bypass exists (`_parse_token`) for local testing — confirm it is test-only.
- Company scoping: `Company` entity; webhooks/interviews must be 403 for a user from another company.

## Webhooks (ATS integration) — highest-risk surface

- **SSRF**: `_validate_webhook_url` resolves hostnames and blocks loopback/private/link-local/reserved IPs; public URLs must be HTTPS. Watch for DNS rebinding (resolve at delivery time, re-validate), IPv6 literal bypasses, redirects.
- **HMAC**: payloads signed `sha256=...` with per-webhook secret. Secret returned **only** on create. Deliveries recorded in `webhook_deliveries` (attempt count, status, timestamps).
- **Retries**: 1s→2s→4s (max `WEBHOOK_MAX_RETRIES=3`, timeout `WEBHOOK_TIMEOUT_SECONDS=10`).
- **DoS**: unbounded delivery history growth; rate limiting on `POST /api/webhooks/{id}/test`.
- **Leakage**: never serialize `secret` or full payload bodies into logs or list responses.

## LLM evaluation (prompt injection)

- `core/evaluator.py` scores candidate answers via Gemini Flash (ollama fallback). Candidate answers are untrusted input.
- Sanitize/system-instruct the scorer so embedded instructions in answers cannot alter verdicts; do not echo raw answers into logs.
- Resume extraction (`core/resume_parser.py`) ingests untrusted `.pdf`/`.docx`/`.doc`/`.txt` — beware of parsers following external references; treat extracted text as data, never as prompts or commands.

## Deployment (Docker/Traefik) — see `examples/` and `checklists/`

- Docker used only for deployment (Traefik reverse proxy, compose profiles). Non-root user, dropped capabilities, resource limits, no secrets baked into images, health checks.
- Never expose FastAPI Uvicorn directly; keep Traefik as the ingress.
- Favor `GET`-only debug instruments; keep admin-only routes behind token checks.

## Input validation

- All boundaries use Pydantic (SQLAlchemy models are ORM-only; request/response schemas live in the API layer). Enforce size limits on answer text and uploads.