# AI Interview Simulator (ARC)

An end-to-end AI-powered interview platform that conducts structured technical and
marketing interviews, parses resumes, generates personalized questions, evaluates
answers in real time, collects voice answers, and surfaces analytics for both
candidates and hiring companies.

**Architecture:** Python `core/` engine + [FastAPI](https://fastapi.tiangolo.com)
`backend/` API + [Next.js](https://nextjs.org) `frontend/web` SPA with role-based
routing, SQLAlchemy persistence (dev SQLite / Supabase-compatible schema), and a
Playwright E2E layer.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Features](#features)
3. [Tech Stack](#tech-stack)
4. [Prerequisites](#prerequisites)
5. [Setup & Installation](#setup--installation)
6. [Running the App](#running-the-app)
7. [Configuration](#configuration)
8. [API Reference](#api-reference)
9. [Testing](#testing)
10. [CI / CD](#ci--cd)
11. [Project Structure](#project-structure)
12. [Security Notes](#security-notes)
13. [Dependency Audits](#dependency-audits)
14. [License](#license)

---

## Architecture Overview

```
                    ┌─────────────────────────────────────────────┐
                    │              frontend/web (Next.js)          │
                    │  (candidate) | (company) | (auth)            │
                    │  voice-interview · campaigns · dashboard     │
                    └───────────────┬─────────────────────────────┘
                                    │ HTTP / JSON  (CORS: localhost:3000)
                    ┌───────────────▼─────────────────────────────┐
                    │             backend/ (FastAPI)               │
                    │  api/  auth · interviews · campaigns ·       │
                    │        company · analytics · domains ·       │
                    │        webhooks                              │
                    │  services/ speech (STT/TTS) · email          │
                    │  db/    SQLAlchemy · SQLite / Supabase       │
                    └───────────────┬─────────────────────────────┘
                 ┌──────────────────┼──────────────────┐
                 │ runs the engine  │                  │
        ┌────────▼────────┐   ┌─────▼─────┐    ┌───────▼──────┐
        │   core/ (pure)  │   │  SQLite   │    │  Supabase     │
        │ engine/evaluator│   │  (dev)    │    │  (prod)       │
        │ resume/questions│   └───────────┘    └───────────────┘
        └────────┬────────┘
                 └── LLM: Gemini via OpenAI SDK, or local Ollama
```

- **`core/`** — pure-Python domain layer (no I/O): interview engine, LLM evaluator
  with retries, resume parser, question engine, model router. Imported by the API.
- **`backend/`** — FastAPI application exposing REST endpoints, persistence
  (SQLAlchemy + SQLite for dev, Supabase schema for prod), webhook dispatch, and
  voice transcription/TTS service.
- **`frontend/web/`** — Next.js 14 app-router SPA. Route groups: `(candidate)`,
  `(company)`, `(auth)`. Includes a simulated-speech voice interview flow.

---

## Features

### Core & Engine (`core/`)
- **Interview orchestration** — question → answer → scoring → follow-up → report.
- **LLM evaluation** — weighted scoring (relevance / clarity / creativity /
  communication), verdicts (Strong / Average / Needs Improvement), retry logic,
  robust JSON parsing.
- **Model router** — sends pre-screen / generate / evaluate / follow-up to the
  lowest-cost capable Gemini model; falls back to Ollama `llama3`.
- **Resume parsing** — PDF (`pdfplumber`), DOCX (`python-docx`), TXT; extracts
  name, email, phone, education, experience, a 133-skill marketing database
  across 8 categories; quality scoring (0–100); experience-level classification.
- **Personalized questions** — 8 templates injecting the candidate's first name,
  skills, titles, and years; role-aware difficulty distribution; anti-repeat
  history; topic coverage; randomized order.
- **Multi-domain question banks** — marketing, software engineering, finance,
  HR, sales.

### Backend API (`backend/`)
- **Auth** — register / login / me with JWT (bcrypt-hashed passwords, 72-byte
  safe pre-hash); role-based access (candidate / company / admin) with dev-mode
  fallback.
- **Interviews** — start session, submit text or **voice** answers
  (`/audio-start`, `/{id}/audio-answer`), fetch next question / follow-up,
  integrity event reporting, hard-lock enforcement, list / get sessions, results.
- **Hard-lock** — session terminates when integrity score < 50 or 3+ serious
  events (tab_switch / face_lost). Locked sessions return 403 on all advance
  endpoints; report still returns data for the locked screen.
- **Campaigns** — companies bulk-upload candidates from CSV/JSON and launch an
  interview campaign with generated invite tokens.
- **Company dashboard** — sessions, candidates, cross-candidate compare,
  analytics.
- **Webhooks + ATS** — register webhook endpoints (HMAC-SHA256 signed payloads,
  retry with backoff, delivery log); SSRF protection on webhook URLs.
- **Services** — `speech.py` (Gemini Flash STT with 429/502/503/504 graceful
  fallback), `email.py` (SMTP invites).

### Frontend (`frontend/web`)
- **Candidate** — voice-enabled interview room (mic via Web Speech + waveform),
  text answers, live question → answer → follow-up, results report, interview
  history.
- **Anti-cheat** — camera-based face detection (native API + motion heuristic),
  integrity scoring with cooldowns and grace periods, paste blocking in answer
  textarea, voice auto-stop on face loss, hard-lock locked screens.
- **Company** — dashboard, sessions, candidates, compare, campaigns (bulk
  invite + email), custom question banks.
- **Auth** — register / login with role-aware post-login redirect.

---

## Tech Stack

| Layer      | Technology                                                            |
|------------|-----------------------------------------------------------------------|
| Backend    | Python 3.10+, FastAPI, Uvicorn, SQLAlchemy, Pydantic v2               |
| Database   | SQLite (dev) / Supabase schema (prod)                                 |
| LLM        | Google Gemini (OpenAI SDK) + Ollama `llama3` fallback                 |
| Frontend   | Next.js 14, React 18, TypeScript, Tailwind CSS                        |
| Voice      | Web Speech API (browser) + Python `speech.py` (STT/TTS)               |
| Testing    | pytest + pytest-cov (backend/core), Vitest + Testing Library (frontend), Playwright (E2E) |
| CI         | GitHub Actions (backend / core / frontend)                            |
| Auth       | PyJWT, passlib[bcrypt]                                                |

---

## Prerequisites

- **Python 3.10+**
- **Node.js 20+** and npm
- **Ollama** (optional — only needed for the local `llama3` fallback):
  `ollama pull llama3`
- **Free port 8000** (backend) and **3000** (frontend)

---

## Setup & Installation

### 1. Clone & Python venv

```bash
git clone <repo-url>
cd "interview v2"

# Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

# Install backend + core dependencies
pip install -r requirements.txt
```

### 2. Frontend dependencies

```bash
cd frontend/web
npm install
cd ../..
```

### 3. Environment variables

Copy `.env.example` to `.env` and fill in values. Critical variables:

| Variable                          | Purpose                                   | Default        |
|-----------------------------------|-------------------------------------------|----------------|
| `GOOGLE_API_KEY`                  | Gemini API key (LLM)                      | *(required)*   |
| `JWT_SECRET_KEY`                  | Token signing secret (≥32 chars)          | *(required)*   |
| `SUPABASE_URL` / `SUPABASE_*_KEY` | Supabase (prod persistence / auth/GoTrue) | local: `:8000` |
| `DATABASE_URL`                    | SQLAlchemy URL (SQLite by default)        | dev SQLite cold |
| `SMTP_*`                          | Email invites (SMTP)                       | gmail defaults |
| `CORS_ORIGINS`                    | Allowed browser origins                   | `http://localhost` |
| `ENV`                             | `development` / `production`              | `development`  |

> `.env` is git-ignored. `.env.*` files are also ignored (`!`.env.example`).
> Never commit real secrets.

---

## Running the App

### Full stack (both servers)

```bash
start_servers.bat        # Windows convenience script
```

### Backend only

```bash
# from repo root, with venv active
python -m uvicorn backend.app:app --reload --port 8000
```

Interactive docs: http://localhost:8000/docs (Swagger UI) and
`/openapi.json`.

### Frontend only

```bash
cd frontend/web
npm run dev              # dev server on :3000
```

Set `frontend/web/.env.local`:

```
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
```

### Production build / E2E

```bash
cd frontend/web
npm run build
npm start                # serves the built app on :3000
```

---

## Configuration

Backend settings live in `config.yaml` (LLM, scoring weights, interview
settings, verdict thresholds, resume, question engine, personas, model routes)
and `backend/app/config.py` (env-driven values, incl. SMTP).

Key tunables in `config.yaml`:

```yaml
llm:
  provider: "gemini"          # or "ollama"
  model: "gemini-3.5-flash"
  fallback_models: [...]
  max_retries: 3

interview:
  question_count: 5
  max_followups_per_question: 1

scoring:
  relevance_weight: 0.3
  clarity_weight: 0.25
  creativity_weight: 0.25
  communication_weight: 0.2

verdicts:
  strong_threshold: 7
  average_threshold: 5

question_engine:
  use_llm_generation: false
  randomize_order: true
```

---

## API Reference

The API is fully self-describing — open `http://localhost:8000/docs` or the
OpenAPI snapshot. Categories:

| Router      | Prefix                | Key endpoints                                            |
|-------------|-----------------------|----------------------------------------------------------|
| Auth        | `/api/auth`           | `register`, `login`, `me`                                |
| Interviews  | `/api/interviews`     | `start`, `audio-start`, `{id}/answer`, `{id}/audio-answer`, `{id}/question`, `{id}/results`, lists |
| Campaigns   | `/api/campaigns`      | `upload` (CSV/JSON bulk), `list`                         |
| Company     | `/api/company`        | `dashboard`, `sessions`, `candidates`, `compare`         |
| Analytics   | `/api/analytics`      | `sessions`                                               |
| Domains     | `/api/domains`        | `list`, detail                                           |
| Webhooks    | `/api/webhooks`       | `register`, `list`, `deliveries`, `{id}/test`, delete    |

> The test suite pins the real shape of these endpoints in
> `backend/tests/test_openapi_contract.py`.

---

## Testing

There are **four** automated Python/JS suites plus a browser E2E layer. Full
details, run commands, and known caveats live in
[`tests/README.md`](tests/README.md). Quick reference:

```powershell
# 1. Backend (80% coverage gate over backend/app, dev DB never touched)
cd backend
..\venv\Scripts\python -m pytest

# 2. Core engine (repo root)
cd "R:\IMP\interview v2"
.\venv\Scripts\python -m pytest test_core.py test_analytics.py test_question_engine.py test_interview_runner.py test_resume.py test_evaluator.py test_mutation_kills.py tests/test_api.py -p no:cacheprovider

# 3. Frontend (Vitest + typecheck + production build)
cd frontend/web
npm run verify

# 4. Browser E2E (fake-device voice)
npm run build          # required once — E2E serves the production build
npm run e2e
```

**Safety rails** baked into the suites:

- Backend tests redirect `DATABASE_URL` to a throwaway temp SQLite DB
  (`backend/tests/conftest.py`) and a guard **fails the run** if the dev
  `interview.db` is ever touched.
- LLM calls are mocked — no API key or Ollama needed to run tests.
- Frontend coverage is scoped to `src/` with an 80% threshold
  (`vitest.config.ts`); backend gate enforces 80% over `backend/app/`
  (excluding static domain data).

### Current verification (green)

- Backend: **268 passed**, 86.50% coverage → gate met
- Core: **214 passed**
- Frontend: **135 Vitest tests + `tsc --noEmit` + `next build`**
- E2E: **2 Playwright specs passed**

---

## CI / CD

`.github/workflows/ci.yml` runs three parallel jobs on push/PR:

1. **Backend** — installs `requirements.txt` + `pytest pytest-cov`, runs the
   full suite with the 80% gate.
2. **Core** — installs requirements, runs the root engine/evaluator/mutation
   suites.
3. **Frontend** — `npm ci`, `npm run verify`, installs Playwright Chromium,
   `npm run e2e`.

---

## Project Structure

```
interview v2/
├── README.md                  # this file
├── requirements.txt           # Python deps (backend + core + tests)
├── config.yaml                # engine / scoring / question settings
├── main.py                    # legacy CLI entry point
├── core/                      # pure domain layer (engine, evaluator, resume...)
│   ├── engine.py              # interview state machine
│   ├── evaluator.py           # LLM calls, weighted scoring, JSON parsing
│   ├── question_engine.py     # personalized questions, difficulty, anti-repeat
│   ├── resume_parser.py       # PDF/DOCX/TXT extraction + skill matching
│   ├── model_router.py        # route to cheapest capable Gemini/Ollama model
│   └── ...
├── backend/
│   ├── app/
│   │   ├── __init__.py        # FastAPI app factory + router registration
│   │   ├── api/               # auth, interviews, campaigns, company, analytics, domains, webhooks
│   │   ├── db/                # database.py, models.py, sessions.py, invites.py, domains.py
│   │   ├── domains/           # per-domain question banks (marketing, se, finance, hr, sales)
│   │   └── services/          # speech.py (STT/TTS), email.py (SMTP)
│   ├── pytest.ini             # -q --cov=app --cov-fail-under=80
│   ├── .coveragerc
│   ├── scripts/
│   │   ├── e2e_server.py      # throwaway temp DB + seeded demo accounts + LLM stub (Playwright webServer)
│   │   └── seed_dev.py        # seed demo users for local dev
│   └── tests/                 # API, auth, db CRUD + isolation, openapi contract, speech
├── frontend/web/
│   ├── src/
│   │   ├── app/               # (candidate) (company) (auth) route groups
│   │   ├── features/
│   │   │   ├── voice-interview/   # mic, waveform, speech hooks, TTS
│   │   │   └── anti-cheat/        # camera monitor, face detector, integrity
│   │   ├── lib/               # api.ts, audio.ts
│   │   └── test/              # setup, test-utils, speech fake
│   ├── e2e/voice-interview.spec.ts
│   ├── playwright.config.ts
│   ├── vitest.config.ts
│   └── package.json
├── tests/README.md            # detailed test-suite guide
└── .github/workflows/ci.yml
```

---

## Security Notes

- **Never commit secrets.** `.env`, `.env.*` are git-ignored; only
  `.env.example` (placeholders) is tracked.
- **JWT** — set a strong `JWT_SECRET_KEY` (≥32 chars) before deploying; the app
  warns loudly if you leave the default.
- **Passwords** — hashed with bcrypt; passwords longer than bcrypt's 72-byte
  limit are pre-hashed with SHA-256.
- **Webhooks** — signed with HMAC-SHA256; signing secret returned once; payload
  signatures verified; SSRF protection blocks private/loopback webhook URLs
  unless explicitly allowed.
- **CORS** — restrict `CORS_ORIGINS` to trusted origins in production.
- **Anti-cheat** — camera monitoring, integrity scoring, and hard-lock session
  termination enforce exam integrity. The system is designed to tolerate honest
  behavior (typing, brief focus shifts) while catching genuine violations
  (sustained tab switching, prolonged face absence, external clipboard usage).

---

## Dependency Audits

- **Backend (Python):** `pip install pip-audit && pip-audit` — currently
  **clean** (keep `pip` itself updated).
- **Frontend (npm):** `npm audit` — currently **5 high-severity advisories**
  rooted in the pinned `next@14.2.35`. The only offered fix is a breaking
  jump to `next@16.3.3`; that migration is tracked separately and should not be
  forced during routine work (the app uses none of the affected surfaces).

---

## License

MIT
