# This Project — Playwright / Browser Checks

The AI Interview Simulator has no Playwright setup yet. This reference documents how to run browser checks when you reach the frontend phase (or for ad-hoc UI verification).

## Local dev servers

- Backend API: FastAPI on **`http://localhost:8000`** (`python -m uvicorn app.__init__:app` from `backend/`, or the repo's run script).
- Frontend: Next.js on **`http://localhost:3000`** (`npm run dev` from `frontend/web/`).

## Useful flows to exercise

1. Register → login as candidate → start an interview for a domain (`/interview/[domain]/[sessionId]`).
2. Company login → create a session / invite → view sessions and candidates.
3. Webhook round-trip: create a webhook, POST a test delivery, check `GET /api/webhooks/{id}/deliveries` shows `delivered`.

## Guidance

- Prefer `playwright.sync_api` scripts (per the skill's `with_server.py` pattern) over full framework installs for quick checks.
- For VM/graphical safety on Windows/PowerShell, launch Chromium headless unless you explicitly need a visible browser.
- If a first run fails because Chrome/Edge binaries are missing, run `python -m playwright install chromium` and retry.
- Treat the API as the source of truth for acceptance checks; the browser is just the harness.