# Test Suites

This project has four automated test suites plus a browser E2E layer. All of
them run in CI (see `.github/workflows/ci.yml`). The Python venv lives at the
repo root: `venv` (`venv\Scripts\python.exe` on Windows, `venv/bin/python` on
Linux/macOS).

```
tests/README.md        <- you are here
backend/tests/         Backend API + DB tests (pytest, TestClient, coverage gate)
<repo root>/test_*.py  Core engine/evaluator unit tests (no pytest.ini here)
frontend/web/src/**    Frontend unit/component tests (vitest + coverage gate)
frontend/web/e2e/      Playwright browser E2E (real FastAPI + built Next.js app)
```

---

## 1. Backend API suite (with coverage gate)

Config in `backend/pytest.ini` and `backend/.coveragerc`. The gate requires
**80% coverage** over `backend/app/` **excluding `backend/app/domains/*`**
(static domain data, mirroring the frontend's vitest scoping).

Safety rails:

- `backend/tests/conftest.py` sets `DATABASE_URL` to a **throwaway temp
  SQLite DB** before the app imports, and registers guard hooks that fail
  loudly if a `session_finish`/`evaluate_main` with a real `interview.db` is
  ever detected. The dev DBs (`interview.db`, `backend/interview.db`) are
  never touched.
- Individual LLM calls are mocked (`core.evaluator._call_llm` and
  `core.engine.pre_screen_answer`) — the suite never needs Ollama/OpenAI.
- `test_db_domains_real.py` exercises the real SQLite helpers by creating the
  Supabase-style `domains/questions/skills/job_titles` tables on the temp
  engine.

Run (from `backend/`):

```powershell
..\venv\Scripts\python -m pytest
```

> Running a *subset* of the suite fails the `--cov-fail-under=80` gate
> (e.g. "total of 41 is less than fail-under=80"). Always run the full suite
> when verifying.

Other checks included here:

- `tests/test_openapi_contract.py` — snapshot of `/openapi.json` (paths, tags,
  schema required/optional fields, no trailing-slash drift). Keeps the
  frontend's `src/lib/api.ts` paths honest.
- `tests/test_db_isolation.py` — verifies temp-DB quarantine still works.

## 2. Core suite (repo root)

The engine/evaluator/question-engine tests live at the repo root (no
`pytest.ini`). They import `core.*` only and run in a few seconds.

```powershell
.\venv\Scripts\python -m pytest test_core.py test_analytics.py test_question_engine.py test_interview_runner.py test_resume.py test_evaluator.py test_mutation_kills.py tests/test_api.py -p no:cacheprovider
```

- `test_evaluator.py` — golden answers for `evaluate_main`, `evaluate_followup`,
  `merge`, and pre-screen logic (40 tests).
- `test_mutation_kills.py` — mini mutation harness: mutates a source line in
  `core/evaluator.py`, re-executes, and asserts the mutation changes behavior.
  Documents a known *surviving* mutant (an unreachable `cfg` fallback default).

## 3. Frontend unit suite (vitest + coverage gate)

Config in `frontend/web/vitest.config.ts` (coverage scoped to `src/`, 80%
threshold). Test environment is jsdom; `src/test/setup.ts` clears
localStorage between tests and stubs media/permission APIs.

```powershell
npm test            # vitest run  (110 tests)
npm run test:coverage
npm run verify      # vitest run && tsc --noEmit && next build
```

ESLint ignores `*.test.{ts,tsx}` by design (`.eslintignore`). If linting
directly, ESLint ≥ 9 needs `$env:ESLint_USE_FLAT_CONFIG="false"` on Windows.

## 4. Playwright E2E (fake-device voice)

Real end-to-end flow against a live FastAPI server and a production build of
the Next.js app.

Setup (once):

```powershell
npm install
npx playwright install chromium
```

Run:

```powershell
npm run build   # required: E2E serves the production build
npm run e2e
```

How it works:

- `playwright.config.ts` starts two web servers (no dev servers needed):
  1. Backend via `backend/scripts/e2e_server.py` — a **throwaway temp SQLite
     DB**, seeded demo accounts (`company@test.io` / `candidate@test.io`,
     password `Passw0rd123!`), and the LLM boundary stubbed for determinism.
     The dev DB is never touched.
  2. `next start` on the built app (`http://127.0.0.1:3000`).
- Chromium launches with `--use-fake-device-for-media-stream` +
  `--use-fake-ui-for-media-stream` so the microphone path needs no real
  device. Because Web Speech is per-browser, the spec injects a deterministic
  `window.SpeechRecognition` fake (`page.addInitScript`) that emits one final
  transcript per recording — this is the "fake device voice".

Specs: `e2e/voice-interview.spec.ts`

- candidate registers → starts a voice interview → answers with the fake mic →
  follow-up → report page;
- demo company signs in → dashboard.

> The E2E backend runs on port 8000. Shut down any dev API server first, or
> the test servers will fail to bind.

## 5. Dependency audits

Frontend (`frontend/web/`):

```powershell
npm audit
```

Current status: **5 high-severity advisories**, all rooted in the pinned
`next@14.2.35` (and its transitive `postcss`). The only resolution npm offers
is a **breaking jump to `next@16.3.3`** (`npm audit fix --force`). That upgrade
touches core routing/react versions and deserves its own migration task — do
not force it during routine work. The app uses none of the affected surfaces
(Server Actions, rewrites), so the practical risk is low.

Backend (Python venv):

```powershell
pip install pip-audit
.\venv\Scripts\pip-audit
```

Current status: **clean** (`No known vulnerabilities found`). Note `pip` itself
was previously flagged — keep it current (`python -m pip install --upgrade pip`).