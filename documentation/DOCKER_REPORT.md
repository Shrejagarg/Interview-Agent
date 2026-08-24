# Docker Implementation Report — Interview Agent v2.0

**Date:** 2026-08-24
**Status:** Analysis + Remediation Plan

---

## 1. Current State

### What Exists
| File | Status |
|---|---|
| `docker-compose.yml` | Exists — 4 services, multiple issues |
| `Dockerfile.backend` | Exists — minimal, dev-grade |
| `frontend/candidate/Dockerfile` | Exists — minimal, no multi-stage |
| `frontend/company/Dockerfile` | **MISSING** (compose references it) |
| `.dockerignore` | **MISSING** |

### Architecture
```
┌─────────────┐   ┌──────────────────┐   ┌──────────────────┐
│  Candidate   │   │     Company       │   │    FastAPI        │
│  Next.js     │──▶│     Next.js       │──▶│    Backend        │
│  :3000       │   │     :3001         │   │    :8000          │
└─────────────┘   └──────────────────┘   └────────┬─────────┘
                                                   │
                                          ┌────────▼─────────┐
                                          │  Supabase/Postgres │
                                          │  :5432             │
                                          └──────────────────┘
```
Plus optional: Gemini API (external), Ollama sidecar (fallback)

---

## 2. Issues Found (14 total)

### P0 — Broken / Won't Start
| # | Issue | Location |
|---|---|---|
| 1 | **Company Dockerfile missing** — `docker-compose.yml` line 43 references `./frontend/company/Dockerfile` which doesn't exist. `docker compose build` fails immediately. | `docker-compose.yml:43` |
| 2 | **requirements.txt incomplete** — Missing `PyYAML`, `filelock`, `pdfplumber`, `python-docx` which `core/` imports. Backend container crashes on first request that touches question engine or resume parsing. | `requirements.txt` |

### P1 — Security / Secrets
| # | Issue | Location |
|---|---|---|
| 3 | **Google API key hardcoded in config.yaml** — `google_api_key: "REDACTED..."` is committed to git. Anyone with repo access has the key. | `config.yaml:12` |
| 4 | **All containers run as root** — No `USER` directive in any Dockerfile. Violates least-privilege. | `Dockerfile.backend`, `candidate/Dockerfile` |

### P2 — Correctness / Runtime
| # | Issue | Location |
|---|---|---|
| 5 | **NEXT_PUBLIC_API_URL baked at build time** — Next.js inlines `NEXT_PUBLIC_*` env vars during `next build`. The compose file passes `env_file: .env` as runtime env, but the client JS already has `http://127.0.0.1:8000` hardcoded from the build. Frontend can't reach backend in Docker networking. | `docker-compose.yml:33`, `frontend/*/src/lib/api.ts` |
| 6 | **Backend bind-mount overrides container** — `volumes: .:/app` replaces the entire `/app` directory with the host filesystem. The `pip install` layer is wasted, and `--reload` is inappropriate for production. | `docker-compose.yml:13-14` |
| 7 | **Frontend Dockerfiles are single-stage** — No multi-stage build. The `node_modules` (400MB+) are shipped in the final image. `npm ci` + `next build` artifacts remain. | `candidate/Dockerfile`, needs company one too |
| 8 | **No `.dockerignore`** — `COPY . .` sends `node_modules/`, `.next/`, `venv/`, `.git/`, `sessions/` to build context. Builds are 10x slower and images bloated. | Root level |
| 9 | **`config.yaml` not injected via env** — Backend reads `config.yaml` from disk via `core/config.py:CONFIG_PATH`. The Dockerfile copies it into the image, but env-specific values (API key) should come from environment variables, not baked-in files. | `core/config.py`, `config.yaml` |

### P3 — Quality / Operations
| # | Issue | Location |
|---|---|---|
| 10 | **No reverse proxy** — Candidate (:3000), Company (:3001), and API (:8000) are exposed as separate ports. Production should have a single entry point. | `docker-compose.yml` |
| 11 | **No multi-platform builds** — Dockerfiles use `python:3.13-slim` and `node:22-alpine` without specifying platform. May break on ARM (Apple Silicon). | All Dockerfiles |
| 12 | **Healthcheck uses Python httpx** — Backend healthcheck runs `python -c "import httpx; httpx.get(...)"` which requires httpx installed. A simple `curl` or `wget` would be more reliable. | `docker-compose.yml:19` |
| 13 | **No volume for sessions state** — `sessions/*.json` and `.asked_questions.json` are written to the filesystem but not persisted via Docker volumes. Container restart loses all state. | `docker-compose.yml` |
| 14 | **No restart policy** — Services don't have `restart: unless-stopped`. Manual restart required after crashes. | `docker-compose.yml` |

---

## 3. Recommended Architecture

### Production Stack
```
                    ┌─────────────┐
                    │   Traefik    │
                    │   Reverse    │
                    │   Proxy      │
                    │   :80/:443   │
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
     ┌────────▼───┐ ┌─────▼──────┐ ┌──▼───────────┐
     │ Candidate   │ │ Company    │ │ FastAPI       │
     │ Next.js     │ │ Next.js    │ │ Backend       │
     │ (standalone)│ │ (standalone│ │ (uvicorn)     │
     │ :3000       │ │ :3001)     │ │ :8000         │
     └─────────────┘ └────────────┘ └──────┬───────┘
                                           │
                                  ┌────────▼─────────┐
                                  │  Postgres          │
                                  │  :5432             │
                                  └──────────────────┘
```

### Deployment Profiles
- **`docker compose up`** — Full production stack (4 services + traefik)
- **`docker compose up --profile dev`** — Development mode (bind-mount, hot reload)
- **`docker compose up --profile llm`** — Adds Ollama sidecar for local LLM

---

## 4. File-by-File Fix Plan

### 4.1 `requirements.txt` — Add Missing Dependencies
```
PyYAML>=6.0
filelock>=3.13
pdfplumber>=0.10.0
python-docx>=1.1.0
```

### 4.2 `.dockerignore` — Create New
```
.git
.venv
venv
node_modules
.next
__pycache__
*.pyc
.pytest_cache
sessions
test_resumes
documentation
verification_report
*.md
.env
.env.local
```

### 4.3 `Dockerfile.backend` — Harden
- Multi-stage: builder + runtime
- Non-root user (`appuser`)
- `COPY requirements.txt` first for layer caching
- Remove `--reload` from CMD (dev-only)
- Healthcheck built-in

### 4.4 `frontend/candidate/Dockerfile` — Multi-stage
- Stage 1 (`deps`): Install dependencies
- Stage 2 (`builder`): Build with `NEXT_PUBLIC_API_URL` as build ARG
- Stage 3 (`runner`): Copy only `.next/standalone` + static
- Enable `output: "standalone"` in `next.config.mjs`
- Non-root user

### 4.5 `frontend/company/Dockerfile` — Create (same pattern)
- Identical structure to candidate
- Port 3000 internally (mapped to 3001 by compose)

### 4.6 `docker-compose.yml` — Rewrite
- Remove `version: "3.8"` (deprecated)
- Add `.env` build args for `NEXT_PUBLIC_API_URL`
- Fix company build context
- Add restart policies
- Add volume for session state
- Add `.dockerignore`-aware contexts
- Add Traefik labels (optional, behind profile)
- Fix healthchecks

### 4.7 `next.config.mjs` (both frontends) — Enable Standalone
```js
const nextConfig = { output: "standalone" };
```
Reduces image size from ~400MB to ~80MB per frontend.

### 4.8 `config.yaml` — Remove Hardcoded Key
- Remove `google_api_key` from file
- Read from `GOOGLE_API_KEY` env var only
- `core/evaluator.py` already falls back to `os.getenv("GOOGLE_API_KEY")`

### 4.9 `.env.example` — Update with All Required Vars
```
# LLM
GOOGLE_API_KEY=your-gemini-api-key
OLLAMA_HOST=http://localhost:11434

# Supabase
SUPABASE_URL=http://localhost:54321
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key

# Frontend build
NEXT_PUBLIC_API_URL=http://localhost:8000

# Database
POSTGRES_PASSWORD=postgres
POSTGRES_DB=interview_agent

# App
ENV=development
CORS_ORIGINS=http://localhost:3000,http://localhost:3001
```

---

## 5. Implementation Order

| Step | Files | Effort |
|---|---|---|
| 1 | Fix `requirements.txt` (add 4 deps) | 2 min |
| 2 | Create `.dockerignore` | 2 min |
| 3 | Remove API key from `config.yaml`, update `core/evaluator.py` to env-only | 5 min |
| 4 | Update `.env.example` with all vars | 2 min |
| 5 | Enable `output: "standalone"` in both `next.config.mjs` | 2 min |
| 6 | Rewrite `Dockerfile.backend` (multi-stage, non-root) | 10 min |
| 7 | Rewrite `frontend/candidate/Dockerfile` (multi-stage, build ARG) | 10 min |
| 8 | Create `frontend/company/Dockerfile` (same pattern) | 5 min |
| 9 | Rewrite `docker-compose.yml` (fix all P0-P2 issues) | 15 min |
| 10 | Test: `docker compose build && docker compose up` | 10 min |
| **Total** | | **~60 min** |

---

## 6. Volumes & State Persistence

| Path | Purpose | Docker Volume |
|---|---|---|
| `/app/sessions/` | Session JSON files (in-memory fallback) | `sessions_data:/app/sessions` |
| `/app/.asked_questions.json` | Anti-repeat tracking | `sessions_data:/app` (shared volume) |
| `/app/interview.log` | Application logs | `logs:/app/logs` |
| `/var/lib/postgresql/data` | Postgres data | `pgdata` (already exists) |

---

## 7. Environment Variable Matrix

| Variable | Backend | Candidate FE | Company FE | DB | Source |
|---|---|---|---|---|---|
| `GOOGLE_API_KEY` | Runtime | - | - | - | `.env` |
| `SUPABASE_URL` | Runtime | - | - | - | `.env` |
| `SUPABASE_ANON_KEY` | Runtime | - | - | - | `.env` |
| `SUPABASE_SERVICE_ROLE_KEY` | Runtime | - | - | - | `.env` |
| `OLLAMA_HOST` | Runtime | - | - | - | `.env` |
| `MODEL_NAME` | Runtime | - | - | - | `.env` |
| `ENV` | Runtime | - | - | - | `.env` |
| `CORS_ORIGINS` | Runtime | - | - | - | `.env` |
| `NEXT_PUBLIC_API_URL` | - | **Build** | ****Build**** | - | Build ARG |
| `POSTGRES_PASSWORD` | - | - | - | Runtime | `.env` |
| `POSTGRES_DB` | - | - | - | Runtime | `.env` |

**Critical**: `NEXT_PUBLIC_API_URL` must be a **build ARG**, not a runtime env var.

---

## 8. Security Checklist

- [ ] Remove Google API key from `config.yaml`
- [ ] Add `.dockerignore` to prevent `.env`, `.git`, `node_modules` from entering build context
- [ ] Add non-root `USER` to all Dockerfiles
- [ ] Don't mount `.env` as a volume (only pass via `env_file`)
- [ ] Use `POSTGRES_PASSWORD` from `.env`, never hardcode
- [ ] Rotate the exposed Google API key (it was in git history)

---

## 9. Build Size Estimates (After Fixes)

| Image | Before | After | Reduction |
|---|---|---|---|
| Backend | ~800MB | ~250MB | Multi-stage + slim |
| Candidate FE | ~1.2GB | ~80MB | Standalone output |
| Company FE | N/A | ~80MB | Standalone output |
| **Total** | ~2GB+ | ~410MB | **~80% smaller** |

---

## 10. Quick Test Commands

```bash
# Build everything
docker compose build

# Run in dev mode (hot reload)
docker compose --profile dev up

# Run in production mode
docker compose up -d

# Check health
curl http://localhost:8000/health

# View logs
docker compose logs -f backend
```

---

## 11. Decision Points (Need User Input)

1. **Reverse proxy**: Add Traefik/Nginx, or keep separate ports?
2. **Supabase strategy**: Hosted Supabase (current dev mode works without it) vs local `supabase/postgres` container vs full Supabase CLI stack?
3. **Ollama**: Include as optional service (profile), or remove entirely since using Gemini?
4. **Production vs Dev compose**: Single file with profiles, or separate `docker-compose.prod.yml`?
