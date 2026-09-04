# Antigravity Handoff — Project State & Context

## What Is This Project

**AI Interview Simulator (ARC)** — a full-stack platform that conducts AI-powered technical/marketing interviews. It parses resumes, generates personalized questions, evaluates answers with LLMs, collects voice answers, and enforces exam integrity through camera monitoring and input analysis.

**Owner:** Shrejagarg | **Branch:** `phase1-backend-refactor`

---

## What We Built (From Scratch)

Everything below was implemented during this phase:

### 1. Camera-Based Anti-Cheat System (`frontend/web/src/features/anti-cheat/`)

**Files created:**
- `faceDetector.ts` — Two face detection strategies: NativeFaceDetector API (Chrome/Edge) + motion heuristic fallback (Firefox/Safari)
- `faceDetector.test.ts` — 10 tests covering grayscale conversion, motion scoring, native strategy, motion detector
- `useCameraMonitor.ts` — Camera permission → frame sampling → face detection → state machine (prompting → active ↔ face_lost → denied/unsupported)
- `useCameraMonitor.test.ts` — 5 tests covering unsupported, denied, no device, sustained absence → face_lost, recovery → face_return
- `CameraMonitor.tsx` — Presentational component showing video preview + status label (receives `videoRef` + `status` from parent)
- `CameraMonitor.test.tsx` — 5 tests covering disabled, active, denied, unsupported, face_lost states
- `AntiCheatIndicator.tsx` — Live integrity score badge (color-coded green/yellow/red)

### 2. Input Monitoring & Integrity Scoring (`useAntiCheat.ts`)

**What it does:**
- Monitors `visibilitychange` (tab switch), `window.blur`, `document.copy`, `document.paste`
- Reports events to backend which calculates integrity score
- Returns `integrityScore`, `locked`, `lockedReason`

**Tuning (important for future work):**
- **3-second blur grace period** — short focus losses (< 3s) are ignored (notification popup, quick alt-tab)
- **10-second cooldown per event type** — prevents rapid-fire penalties
- **Textarea exclusion** — copy/paste events inside `<textarea>` or `<input>` are ignored (normal editing)
- **Paste blocking** — answer textarea has `onPaste` handler calling `preventDefault()` + visual hint
- Face detector needs **6 consecutive absent frames** (3 seconds) before triggering face_lost

### 3. Backend Hard-Lock (`backend/app/api/interviews.py`)

**Constants:**
```python
LOCK_SCORE_THRESHOLD = 50          # lock when integrity score < 50
LOCK_SERIOUS_EVENT_COUNT = 3       # OR after 3+ tab_switch/face_lost events
SERIOUS_LOCK_EVENTS = ("tab_switch", "face_lost")
```

**Functions:**
- `_is_session_locked(state)` — checks both score threshold and event count
- `_ensure_not_locked(state)` — raises HTTP 403 if locked
- Called in: `submit_integrity_event`, `get_current_question`, `submit_answer`, `submit_followup`, `submit_audio_answer`, `submit_audio_followup`
- Report endpoint does NOT 403 (frontend needs data for locked screen)

**Backend integrity scoring (`core/state.py:98`):**
- -15 per flag (except time_limit: -10)
- -5 per skipped answer
- min 0, max 100

### 4. Voice Auto-Stop on Face Loss (`VoiceInterview.tsx`)

```tsx
useEffect(() => {
  if (!blocked) return;
  if (phase === "recording") {
    setPhase("question");
    setHint("Recording paused — face out of view.");
    void stopListening();  // discards the blob — not submitted
  }
}, [blocked, phase, stopListening]);
```

### 5. Locked Session Screens

- **Interview page** (`page.tsx` ModeSwitch): Detects `locked` → shows "Integrity Policy Violated" screen → "View Report" button
- **Results page** (`results/[sessionId]/page.tsx`): Detects `report.locked` → shows locked screen with score, reason → "View History" + "New Interview" buttons
- **History page** (`history/page.tsx`): `locked` status renders in red badge

### 6. API Type Updates (`lib/api.ts`)

- `IntegrityEventResponse`: added `locked?: boolean`, `locked_reason?: string | null`
- `Report`: added `locked?: boolean`, `locked_reason?: string | null`, `integrity_score?: number`
- `useAntiCheat` hook returns `locked` and `lockedReason` state

### 7. STT Graceful Fallback (`backend/app/services/speech.py`)

- 429/502/503/504 from Gemini API → returns placeholder text instead of crashing
- Test added: `test_gemini_service_unavailable_falls_back_gracefully`

### 8. Invite Bank Migration

- Backend: `bank_id` field migration for invite flow

---

## Where the Project Stands Now

### All Tests Green

| Suite | Count | Coverage |
|-------|-------|----------|
| Backend | 268 | 86.50% (gate: 80%) |
| Frontend | 135 | — |
| TypeScript | tsc --noEmit | 0 errors |
| Build | next build | Passing |

### Key Files Modified/Created

| File | What Changed |
|------|-------------|
| `frontend/web/src/features/anti-cheat/*` | Entire feature created (8 files) |
| `frontend/web/src/features/voice-interview/VoiceInterview.tsx` | Auto-stop effect, `blocked` prop |
| `frontend/web/src/app/(candidate)/interview/[domain]/[sessionId]/page.tsx` | Camera monitor, face-lost banner, blocked inputs, locked screen, paste blocking |
| `frontend/web/src/app/(candidate)/results/[sessionId]/page.tsx` | Locked screen rendering |
| `frontend/web/src/app/(candidate)/history/page.tsx` | Red badge for locked status |
| `frontend/web/src/lib/api.ts` | `locked`/`locked_reason`/`integrity_score` on types |
| `backend/app/api/interviews.py` | Hard-lock logic (_is_session_locked, _ensure_not_locked, constants, locked response fields) |
| `backend/app/services/speech.py` | 502/503/504 graceful fallback |
| `backend/tests/test_integrity.py` | TestHardLock (5 tests) |
| `backend/tests/test_speech_service.py` | 503 fallback test |

### What's Deferred

- **Supabase** — user explicitly deferred ("for now lets skip supabase integration"). Backend connects only via `DATABASE_URL`. Dev runs on local SQLite.
- **Gemini STT quota** — free-tier rate limits cause 429/503. Graceful fallback is in place.
- **Graphify graph** — stale (built Aug 30), doesn't include anti-cheat additions.

### How to Verify

```powershell
# Backend (86.50% coverage)
cd backend
..\venv\Scripts\python -m pytest tests/ -x -q --tb=short

# Frontend (135 tests)
cd frontend/web
npx vitest run

# TypeScript
cd frontend/web
npx tsc --noEmit

# Full frontend verify
cd frontend/web
npm run verify
```

### Anti-Cheat Thresholds (Quick Reference)

| Parameter | Value | Location |
|-----------|-------|----------|
| `absentConfirms` | 6 frames (3s) | `useCameraMonitor.ts` |
| `sampleIntervalMs` | 500ms | `useCameraMonitor.ts` |
| Blur grace period | 3,000ms | `useAntiCheat.ts` |
| Event cooldown | 10,000ms | `useAntiCheat.ts` |
| `LOCK_SCORE_THRESHOLD` | 50 | `interviews.py` |
| `LOCK_SERIOUS_EVENT_COUNT` | 3 | `interviews.py` |
| Integrity flag severity | -15 (tab/face/blur/clipboard) | `interviews.py` |
| Time limit severity | -10 | `interviews.py` |
| Skip severity | -5 | `core/state.py` |

### Design Tokens

- Accent: `#FF2A85` (brutal-pink)
- Background: `#0A0A0A` (brutal-dark)
- Font: `var(--font-heading)` = "Space Grotesk"
- All-caps brutalist UI throughout

---

*Generated September 4, 2026.*
