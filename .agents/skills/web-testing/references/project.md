# This Project — Frontend Testing (Planned Stack)

The `frontend/web` app **has no test framework installed yet**. This reference documents the intended stack so that when tests are added they follow `web-testing` conventions.

## Intended setup (when frontend testing starts)

- **Vitest** + **Testing Library** (React) + `jsdom` environment, with **MSW** for API mocking, co-located in `frontend/web/`.
- `npm` scripts mirroring the skill's quick start: `test` → `vitest run`, `test:watch` → `vitest`.
- Config intended to live at `frontend/web/vitest.config.ts` with a `setup.ts` registering Testing Library cleanup.

## Targets worth covering first

1. Candidate interview flow (`src/app/(candidate)/interview` and `interview/[domain]/[sessionId]`) — question render, answer submit, results.
2. Company dashboard/sessions lists (`src/app/(company)/dashboard`, `sessions`) — data loading + empty/loading/error states.
3. Auth pages (`src/app/(auth)/login`, `register`) — form validation and error display.

## Golden rules

- Component tests test behavior, not implementation; mock at the network boundary with MSW, not by mocking modules.
- Add boundary/edge cases per the skill's checklist (empty data, malformed score, missing session id).
- Vitest config lives with the frontend — don't wire it into the Python backend test suite.
- Do **not** install or configure this tooling during backend-phase work; this is documentation-only until the frontend phase.