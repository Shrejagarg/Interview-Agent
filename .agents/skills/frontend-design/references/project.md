# This Project — Frontend Aesthetic Brief

The app is the **AI Interview Simulator**: two user portals plus auth.

## What exists

- Styling is Tailwind (`frontend/web/src/app/globals.css`), App Router in `src/app/`, two persona groups: `(candidate)` and `(company)`, plus `(auth)`.
- Existing pages: auth login/register; candidate interview (`/interview/[domain]/[sessionId]`), results, history; company dashboard, sessions, candidates, compare, invite.

## Design intent to preserve

- Two distinct but **visually consistent** portals — candidate experience should feel calm, focused, low-anxiety; company experience should feel capability-heavy and data-dense (scores, sessions, comparisons).
- Candidate-facing emphasis: a clean focal surface for one question at a time, clear progress affordances, results presented as an action plan (strengths, gaps, recommendations), not just numbers.
- Company-facing emphasis: score distribution vs 7/5 thresholds, trending/gap surfaces, candidate comparison readability.
- Ground choices in the interview/testing subject matter: exam-session, evaluation, and practice — not generic SaaS gradients.

## How to work with this skill here

- When building/reshaping any UI, first read `web-Development/references/project.md` for structure, then use this skill for the aesthetic direction.
- If you're unsure where the design should go, read the existing portal pages before proposing changes so the new work continues their language.
- Take one deliberate, justifiable risk per meaningful screen instead of decorating everything.