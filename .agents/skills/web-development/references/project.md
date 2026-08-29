# This Project — AI Interview Simulator (Frontend)

Act as the frontend engineer on **interview-agent**. Apply the skill's architecture guidance, adapted to the concrete app below.

## Stack & layout

- Next.js **14.2.35** (App Router), React 18, TypeScript, Tailwind. Project lives in `frontend/web/`.
- Source root is `src/`, so App Router files live under **`src/app/`** (not `app/`).
- No fetch/data layer library is set up; the app calls the FastAPI backend directly. No test framework installed yet (Vitest/Playwright planned — see `web-testing`/`webapp-testing` project references).

## Existing routes

```
src/app/
  layout.tsx, globals.css, loading.tsx, page.tsx
  (auth)/login, (auth)/register
  (candidate)/interview
  (candidate)/interview/[domain]/[sessionId]
  (candidate)/results/[sessionId]
  (candidate)/history
  (company)/dashboard, (company)/candidates
  (company)/sessions, (company)/sessions/[sessionId]
  (company)/compare, (company)/invite
```

Two persona route groups exist: `(candidate)` and `(company)`. Keep that structure; add features inside the owning group. The root `(auth)` group holds auth pages.

## Conventions

- Server Components by default; reach for `"use client"` only for interactivity.
- Tailwind for styling — match the existing utility patterns in the rest of the app, don't introduce a component library.
- The API base points at the FastAPI backend (dev: `http://localhost:8000`); do not hardcode secrets or tokens into the client.
- Apply the `frontend-design` skill for anything that needs to look distinctive; keep the two portals visually consistent with each other.

## Golden rules

- Never consume raw API payloads in components without a typed shape at the boundary.
- Smaller route files that compose from shared components — keep route files thin.
- Match existing naming/formatting; there is no lint config beyond ESLint defaults yet.
- Verify with `npm run build` from `frontend/web/` before finishing; the dev server runs via `npm run dev -p 3000`.