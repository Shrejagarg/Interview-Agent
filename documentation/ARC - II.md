# ARC - II: Dual-Frontend Interview Platform

## Overview

This arc transforms the project from a single-candidate CLI/web app into a **two-sided platform**:
- **Candidate Frontend** - Practice interviews across 5 domains
- **Company Frontend** - Conduct interviews, view candidates, compare results

**Tech Stack**: Next.js 14 (App Router) + TypeScript + Tailwind CSS + FastAPI + Ollama (LLM) + Supabase (Auth)

**Approach**: Function-first. No design polish. Get both apps working end-to-end.

---

## Phase 1: Backend - Company Endpoints & Session Ownership

**Goal**: Extend the FastAPI backend to support company-specific operations.

### 1.1 Session Ownership

| Change | Detail |
|--------|--------|
| Add `user_id` field to session store | When candidate starts interview, record their `user_id` |
| Add `company_id` field to sessions | When company invites a candidate, link session to company |
| Filter sessions by ownership | Candidates see only their sessions; companies see sessions they are linked to |

**File**: `backend/app/api/interviews.py`
- Modify `start_interview()` to accept optional `user_id` from JWT
- Store `user_id` in session dict
- Modify `list_sessions()` to filter by `user_id`

### 1.2 Company API Endpoints

**New file**: `backend/app/api/company.py`

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/company/dashboard` | GET | Company stats: total sessions, unique candidates, avg score, domain breakdown |
| `/api/company/sessions` | GET | List all sessions for this company (with filters: domain, status, date range) |
| `/api/company/sessions/{session_id}` | GET | Full session detail (all answers, scores, recommendations) |
| `/api/company/candidates` | GET | List unique candidates with their best scores per domain |
| `/api/company/compare` | GET | Compare 2+ sessions side-by-side (reuses analytics comparison logic) |
| `/api/company/invite` | POST | Create interview invitation (generates invite link with token) |

### 1.3 Role-Based Access Control

**File**: `backend/app/api/auth.py`
- Add `require_role(role: str)` dependency function
- Company endpoints use `Depends(require_role("company"))`
- Candidate endpoints remain open (or add `Depends(require_role("candidate"))` later)

### 1.4 Register New Router

**File**: `backend/app/__init__.py`
- Import and mount `company.router` at `/api/company`

### 1.5 Tests

**New file**: `backend/tests/test_company.py`
- Test dashboard returns stats
- Test sessions list filters by company
- Test session detail returns full data
- Test candidates list with scores
- Test compare endpoint
- Test invite creates token
- Test role enforcement (candidate cannot access company endpoints)

**Estimated**: ~5 files, ~500 lines

---

## Phase 2: Candidate Frontend - Critical Fixes

**Goal**: Fix bugs that prevent the app from working properly.

### 2.1 Fix Auth Token Sending

**File**: `src/lib/api.ts`

**Problem**: `request()` never sends the JWT token. Only `getMe()` does manually.

**Fix**:
- Read token from `localStorage` inside `request()`
- Attach `Authorization: Bearer <token>` header to all requests
- Remove manual header from `getMe()` (now handled by `request()`)

### 2.2 Add Route Protection

**New file**: `src/middleware.ts`

| Route | Auth Required | Behavior |
|-------|--------------|----------|
| `/` | No | Public |
| `/login` | No | Redirect to `/interview` if logged in |
| `/register` | No | Redirect to `/interview` if logged in |
| `/interview` | Yes | Redirect to `/login` if not logged in |
| `/interview/*` | Yes | Redirect to `/login` if not logged in |
| `/history` | Yes | Redirect to `/login` if not logged in |
| `/results/*` | Yes | Redirect to `/login` if not logged in |

### 2.3 Add Layout Metadata

**File**: `src/app/layout.tsx`
- Add `<title>` tag (e.g., "Interview Agent")
- Add `<meta name="description">`
- Import Geist fonts (files exist in `src/app/fonts/` but are unused)

### 2.4 Extract Reusable Components

**New directory**: `src/components/`

| Component | Used In | What It Does |
|-----------|---------|-------------|
| `Nav.tsx` | `layout.tsx` | Navigation bar with links + auth state |
| `QuestionCard.tsx` | `interview/[domain]/[sessionId]/page.tsx` | Displays question + textarea + submit button |
| `ScoreBar.tsx` | `results/[sessionId]/page.tsx` | Colored horizontal bar showing score |
| `SessionTable.tsx` | `history/page.tsx` | Table listing sessions with status/actions |
| `DomainCard.tsx` | `page.tsx` (home) | Card showing domain name + description |

### 2.5 Add Loading States

**New files**:
- `src/app/loading.tsx` - Root loading indicator
- `src/app/interview/loading.tsx`
- `src/app/history/loading.tsx`

### 2.6 Minor UX Fixes

- Show "Interview complete! Redirecting..." message properly before auto-redirect
- Better error messages when API is unreachable
- Disable submit button while evaluating (already done, verify)

**Estimated**: ~8 files, ~350 lines

---

## Phase 3: Company Frontend - New App

**Goal**: Build a functional Next.js app for companies to manage interviews.

### 3.1 Scaffold

```
frontend/company/
  src/
    app/
      layout.tsx
      page.tsx              (dashboard)
      loading.tsx
      login/page.tsx
      register/page.tsx
      sessions/
        page.tsx            (session list)
        [sessionId]/page.tsx (session detail)
      candidates/page.tsx   (candidate list)
      compare/page.tsx      (side-by-side comparison)
      domains/page.tsx      (browse domains)
    components/
      Nav.tsx
      StatsCard.tsx
      SessionTable.tsx
      CompareView.tsx
    lib/
      api.ts
      auth.tsx
  public/
  package.json
  tsconfig.json
  tailwind.config.ts
  postcss.config.mjs
  next.config.mjs
  .env.local
  Dockerfile
```

**Stack**: Same as candidate - Next.js 14, React 18, TypeScript, Tailwind

### 3.2 Pages - Detailed Spec

#### `/` - Dashboard
- Fetch: `GET /api/company/dashboard`
- Display: Total sessions, unique candidates, average score, domain breakdown
- Quick links: View sessions, browse domains, compare candidates

#### `/login` - Company Login
- Same auth flow as candidate (Supabase Auth)
- On login, check `role === "company"` - redirect to dashboard
- If role is "candidate", show error or redirect to candidate app

#### `/register` - Company Registration
- Email, password, company name
- Register with `role: "company"`

#### `/sessions` - Session List
- Fetch: `GET /api/company/sessions?domain=X&status=Y`
- Filters: Domain dropdown, status (in_progress/completed), date range
- Table: Candidate name, domain, status, score, date, actions
- Click row -> `/sessions/{sessionId}`

#### `/sessions/[sessionId]` - Session Detail
- Fetch: `GET /api/company/sessions/{sessionId}`
- Display: Candidate info, domain, experience level, overall score, verdict
- Topic score breakdown with bars
- Per-answer review: question, answer, score, strengths, weaknesses
- Recommendations

#### `/candidates` - Candidate List
- Fetch: `GET /api/company/candidates`
- Table: Name, email, best score per domain, total interviews, avg score
- Click -> view their sessions

#### `/compare` - Compare Candidates
- Fetch: `GET /api/company/compare?session_ids=a,b`
- UI: Select 2+ sessions from dropdown
- Display: Side-by-side topic scores, rankings, delta comparison

#### `/domains` - Browse Domains
- Fetch: `GET /api/domains`
- Cards for each domain: name, description, question count
- Click -> `GET /api/domains/{slug}/questions` to preview questions

### 3.3 API Client

**File**: `src/lib/api.ts`

New endpoints (in addition to shared ones):
```typescript
getCompanyDashboard()
getCompanySessions(filters?)
getCompanyCandidates()
compareCompanySessions(sessionIds: string[])
inviteCandidate(email: string, domainSlug: string, questionCount: number)
getCompanySession(sessionId: string)
```

### 3.4 Auth

**File**: `src/lib/auth.tsx`
- Same pattern as candidate (React Context, localStorage)
- On login, verify role is "company"
- Store role in auth context

### 3.5 Middleware

**File**: `src/middleware.ts`
- `/login`, `/register` - public
- All other routes - require auth
- Dashboard, sessions, candidates, compare, domains - require `role === "company"`

**Estimated**: ~15 files, ~900 lines

---

## Phase 4: Integration & Verification

**Goal**: Make sure everything works together.

### 4.1 End-to-End Flow Test

**Candidate flow**:
1. Register as candidate -> Login -> See domain list
2. Pick domain -> Start interview -> Answer questions -> Get scores
3. View results -> View history

**Company flow**:
1. Register as company -> Login -> See dashboard
2. View sessions -> See candidate results
3. Compare candidates -> View domain questions

### 4.2 Backend Test Additions

**File**: `backend/tests/test_company.py` - ~15 new tests
**File**: `backend/tests/test_api.py` - Update existing tests for session ownership

### 4.3 Cross-Frontend Verification

- Candidate completes interview -> Session appears in company dashboard
- Company can view candidate's full answers and scores
- Company can compare multiple candidates

**Estimated**: ~3 files, ~300 lines

---

## File Change Summary

| Phase | New Files | Modified Files | Lines (est.) |
|-------|-----------|---------------|-------------|
| Phase 1 (Backend) | `company.py`, `test_company.py` | `__init__.py`, `auth.py`, `interviews.py` | ~500 |
| Phase 2 (Candidate FE) | `middleware.ts`, 5 components, 3 loading | `api.ts`, `layout.tsx` | ~350 |
| Phase 3 (Company FE) | ~15 files (full app) | - | ~900 |
| Phase 4 (Integration) | - | `test_api.py`, `test_company.py` | ~300 |
| **Total** | **~23 new** | **~6 modified** | **~2050** |

---

## Execution Order

1. **Phase 1 first** - Backend needs company endpoints before company frontend can exist
2. **Phase 2 in parallel** - Candidate fixes are independent of backend changes
3. **Phase 3 after Phase 1** - Company frontend depends on company API endpoints
4. **Phase 4 last** - Integration testing after everything is built

---

## What is NOT in This Phase

- Docker/deployment (later arc)
- Custom question banks for companies (next arc)
- Supabase data persistence (sessions stay in-memory)
- PDF export / share results
- Real-time features (WebSocket, live updates)
- Advanced UI/polish (design later)
- Company frontend "create custom interview" feature
