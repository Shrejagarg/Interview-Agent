# AI Interview Simulator (ARC) — Full Project Report

**Owner:** Shrejagarg  
**Branch:** `phase1-backend-refactor`  
**Date:** September 4, 2026  
**Status:** All systems operational — 268 backend tests (86.50% coverage), 135 frontend tests, TypeScript clean, production build passing.

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Architecture](#2-architecture)
3. [Core Engine (`core/`)](#3-core-engine-core)
4. [Backend API (`backend/`)](#4-backend-api-backend)
5. [Frontend (`frontend/web/`)](#5-frontend-frontendweb)
6. [Anti-Cheat System](#6-anti-cheat-system)
7. [Voice Interview Pipeline](#7-voice-interview-pipeline)
8. [Tech Stack](#8-tech-stack)
9. [Test Coverage](#9-test-coverage)
10. [How It Helps](#10-how-it-helps)
11. [Deferred & Known Limitations](#11-deferred--known-limitations)
12. [Verification Commands](#12-verification-commands)

---

## 1. Executive Summary

The AI Interview Simulator is a full-stack platform that conducts structured technical and marketing interviews autonomously using LLMs. It parses resumes, generates personalized questions, evaluates answers with weighted scoring, collects voice answers via Web Speech API, enforces exam-integrity policies through camera monitoring and input analysis, and surfaces analytics for both candidates and hiring companies.

The system is built on three layers — a pure-Python domain engine, a FastAPI REST backend, and a Next.js 14 frontend — connected via HTTP/JSON. It supports multiple interview domains (marketing, software engineering, finance, HR, sales), role-based authentication, invite-based flows, campaign management with bulk candidate upload, webhook integration with HMAC-SHA256 signing, and a full anti-cheat proctoring system with camera-based face detection, input monitoring, integrity scoring, and hard-lock session termination.

---

## 2. Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        frontend/web (Next.js 14)                           │
│                                                                             │
│  Route Groups:                                                              │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────────┐   │
│  │ (candidate)  │ │  (company)   │ │   (auth)     │ │   join/          │   │
│  │ interview/   │ │ dashboard/   │ │ login/       │ │   invite flow    │   │
│  │ results/     │ │ sessions/    │ │ register/    │ │                  │   │
│  │ history/     │ │ candidates/  │ │              │ │                  │   │
│  │              │ │ compare/     │ │              │ │                  │   │
│  │              │ │ campaigns/   │ │              │ │                  │   │
│  │              │ │ custom/      │ │              │ │                  │   │
│  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────────┘   │
│                                                                             │
│  Features:                                                                  │
│  ┌─────────────────────────────┐ ┌─────────────────────────────────────┐    │
│  │ voice-interview/            │ │ anti-cheat/                         │    │
│  │ MicButton, VoiceWaveform,   │ │ CameraMonitor, AntiCheatIndicator,  │    │
│  │ useMediaRecorder,           │ │ useAntiCheat, useCameraMonitor,     │    │
│  │ useSpeechRecognition,       │ │ faceDetector (Native + Motion)      │    │
│  │ useSpeechSynthesis          │ │                                     │    │
│  └─────────────────────────────┘ └─────────────────────────────────────┘    │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                │ HTTP / JSON (CORS: localhost:3000)
┌───────────────────────────────▼─────────────────────────────────────────────┐
│                        backend/ (FastAPI)                                    │
│                                                                             │
│  API Routers:                                                               │
│  ┌──────────┐ ┌────────────┐ ┌───────────┐ ┌──────────┐ ┌──────────────┐  │
│  │ auth     │ │ interviews │ │ campaigns │ │ company  │ │ webhooks     │  │
│  │ register │ │ start      │ │ upload    │ │ dashboard│ │ register     │  │
│  │ login    │ │ audio-*    │ │ list      │ │ sessions │ │ deliver      │  │
│  │ me       │ │ question   │ │           │ │ compare  │ │ test         │  │
│  │          │ │ integrity  │ │           │ │ custom   │ │ HMAC-SHA256  │  │
│  └──────────┘ └────────────┘ └───────────┘ └──────────┘ └──────────────┘  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐                   │
│  │ domains  │ │ reports  │ │ analytics│ │ custom banks │                   │
│  │ list     │ │ results  │ │ sessions │ │ CRUD + upload│                   │
│  └──────────┘ └──────────┘ └──────────┘ └──────────────┘                   │
│                                                                             │
│  Services:                                                                  │
│  ┌────────────────────────┐ ┌────────────────────────┐                     │
│  │ speech.py              │ │ email.py               │                     │
│  │ STT: Gemini Flash REST │ │ SMTP invites           │                     │
│  │ TTS: native browser    │ │                        │                     │
│  └────────────────────────┘ └────────────────────────┘                     │
│                                                                             │
│  DB Layer (SQLAlchemy):                                                     │
│  ┌────────┐ ┌──────────┐ ┌────────┐ ┌────────┐ ┌──────────┐ ┌──────────┐  │
│  │models  │ │sessions  │ │credits │ │domains │ │invites   │ │shares    │  │
│  │        │ │          │ │        │ │        │ │          │ │          │  │
│  └────────┘ └──────────┘ └────────┘ └────────┘ └──────────┘ └──────────┘  │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                │
                    ┌───────────┴───────────┐
                    │                       │
            ┌───────▼────────┐    ┌─────────▼────────┐
            │  core/ (pure)  │    │   SQLite (dev)    │
            │                │    │  or Supabase      │
            │ engine.py      │    │  (prod)           │
            │ evaluator.py   │    └───────────────────┘
            │ question_engine│
            │ resume_parser  │
            │ model_router   │
            │ state.py       │
            │ report.py      │
            └───────┬────────┘
                    │
                    ▼
            LLM: Gemini Flash via REST API
                 or Ollama llama3 (fallback)
```

### Data Flow — Interview Lifecycle

```
Candidate starts interview
        │
        ▼
┌───────────────────┐     ┌──────────────┐     ┌──────────────┐
│ POST /start       │────▶│ core/engine  │────▶│ question_    │
│ domain + count    │     │ state machine│     │ engine.py    │
└───────────────────┘     └──────────────┘     └──────┬───────┘
                                                      │
        ┌─────────────────────────────────────────────┘
        ▼
┌───────────────┐     ┌──────────────┐     ┌──────────────┐
│ GET /question │────▶│ evaluator.py │────▶│ LLM (Gemini) │
│ next Q + TTS  │     │ weighted     │     │ score +      │
│               │     │ scoring      │     │ feedback     │
└───────────────┘     └──────────────┘     └──────────────┘
        │
        ▼
┌───────────────┐     ┌──────────────┐     ┌──────────────┐
│ POST /answer  │────▶│ integrity    │────▶│ anti-cheat   │
│ text or audio │     │ check        │     │ events       │
└───────────────┘     └──────────────┘     └──────────────┘
        │
        ▼ (repeat for each question)
┌───────────────┐
│ GET /results  │  Final report: scores, verdict,
│               │  recommendations, integrity status
└───────────────┘
```

---

## 3. Core Engine (`core/`)

The `core/` directory is a pure-Python domain layer with zero I/O dependencies. It is imported by the FastAPI backend and runs all interview logic.

| Module | Purpose |
|--------|---------|
| `engine.py` | Interview state machine — orchestrates the question → answer → scoring → follow-up → report lifecycle |
| `evaluator.py` | LLM-powered answer evaluation — weighted scoring (relevance 0.3, clarity 0.25, creativity 0.25, communication 0.2), verdicts (Strong/Average/Needs Improvement), retry logic, robust JSON parsing |
| `question_engine.py` | Personalized question generation — 8 templates injecting candidate's name, skills, titles, experience; role-aware difficulty distribution; anti-repeat history; topic coverage; randomized order |
| `resume_parser.py` | PDF (`pdfplumber`), DOCX (`python-docx`), TXT parsing — extracts name, email, phone, education, experience; 133-skill marketing database across 8 categories; quality scoring (0–100); experience-level classification |
| `model_router.py` | Routes LLM requests to the cheapest capable Gemini model; falls back to Ollama `llama3` |
| `state.py` | Interview state management — integrity score calculation (-15 per flag, -10 time_limit, -5 skip), session persistence, export |
| `report.py` | Final report generation — scores, verdicts, recommendations |
| `analytics.py` | Cross-session analytics computation |
| `question_bank.py` | Multi-domain question banks (marketing, SE, finance, HR, sales) |
| `skills_database.py` | 133-skill marketing database across 8 categories |
| `domain_bridge.py` | Bridges domain configuration to the engine |
| `custom_bank.py` | User-created custom question bank management |
| `config.py` | YAML-based configuration loading |
| `interviewer.py` | Interview persona configuration |
| `user_profile.py` | Candidate profile construction from resume data |

### Integrity Scoring (`core/state.py`)

```python
score = 100
for flag in state["seriousness_flags"]:
    if flag["reason"] == "time_limit_exceeded":  score -= 10
    else:                                         score -= 15  # tab_switch, face_lost, blur, clipboard
for ans in state["answers"]:
    if ans["evaluation"]["_skipped"]:             score -= 5
return max(0, score)
```

---

## 4. Backend API (`backend/`)

FastAPI application exposing REST endpoints with SQLAlchemy persistence.

### API Routers

| Router | Prefix | Key Endpoints | Purpose |
|--------|--------|---------------|---------|
| `auth.py` | `/api/auth` | `register`, `login`, `me` | JWT auth, bcrypt hashing, role-based access (candidate/company/admin) |
| `interviews.py` | `/api/interviews` | `start`, `audio-start`, `/{id}/answer`, `/{id}/audio-answer`, `/{id}/question`, `/{id}/integrity`, `/{id}/results` | Full interview lifecycle including hard-lock logic |
| `campaigns.py` | `/api/campaigns` | `upload` (CSV/JSON bulk), `list` | Bulk candidate upload and campaign management |
| `company.py` | `/api/company` | `dashboard`, `sessions`, `candidates`, `compare` | Company dashboard and cross-candidate analytics |
| `analytics.py` | `/api/analytics` | `sessions` | Session analytics and reporting |
| `domains.py` | `/api/domains` | `list`, detail | Domain listing and question bank access |
| `webhooks.py` | `/api/webhooks` | `register`, `list`, `deliveries`, `{id}/test`, delete | Webhook management with HMAC-SHA256 signing, SSRF protection |
| `reports.py` | `/api/reports` | results, shares | Report generation and sharing |
| `custom.py` | `/api/custom` | bank CRUD, upload | Custom question bank management |

### Hard-Lock Logic (`interviews.py`)

```python
LOCK_SCORE_THRESHOLD = 50          # lock when integrity score < 50
LOCK_SERIOUS_EVENT_COUNT = 3       # OR after 3+ tab_switch/face_lost events
SERIOUS_LOCK_EVENTS = ("tab_switch", "face_lost")
```

When locked:
- Session `status` is set to `"locked"` with a `locked_reason`
- All advance endpoints (`submit_answer`, `submit_audio_answer`, `get_current_question`, etc.) return HTTP 403
- The report endpoint still returns data (for the locked screen to display)

### Database Layer (`backend/app/db/`)

| Module | Purpose |
|--------|---------|
| `database.py` | SQLAlchemy engine, session factory, `Base.metadata.create_all`, auto-migration for missing columns |
| `models.py` | ORM models: User, Session, Question, Domain, Campaign, Invite, etc. |
| `sessions.py` | Session CRUD operations |
| `credits.py` | Credit system for interview quotas |
| `custom_banks.py` | Custom question bank persistence |
| `domains.py` | Domain data management |
| `invites.py` | Invite token management |
| `result_shares.py` | Report sharing with expiry and revocation |

### Services

| Service | Purpose |
|---------|---------|
| `speech.py` | Google Gemini Flash REST API for STT; graceful fallback on 429/502/503/504; returns `None` for TTS (forces native browser TTS) |
| `email.py` | SMTP-based invite email dispatch |

---

## 5. Frontend (`frontend/web/`)

Next.js 14 App Router SPA with TypeScript, Tailwind CSS, and Brutalist design tokens.

### Route Groups

#### `(candidate)` — Candidate Experience

| Route | Page | Features |
|-------|------|----------|
| `interview/` | Setup | Domain selection, question count, experience level, text/voice mode toggle |
| `interview/[domain]/[sessionId]/` | Live Interview | Text or voice input, camera monitor, anti-cheat indicator, face-lost banner, paste blocking, locked screen |
| `results/[sessionId]/` | Report | Full score report, per-question breakdown, strengths/weaknesses, locked screen |
| `history/` | History | Past interviews with status badges (completed/locked/in_progress) |

#### `(company)` — Company Experience

| Route | Page | Features |
|-------|------|----------|
| `dashboard/` | Dashboard | Overview metrics, recent sessions |
| `sessions/` | Sessions | Session list with filters |
| `candidates/` | Candidates | Candidate management |
| `compare/` | Compare | Cross-candidate comparison |
| `campaigns/` | Campaigns | Campaign creation and management |
| `custom/` | Custom Banks | Custom question bank creation |
| `custom/new` | New Bank | Bank creation form |
| `custom/[bankId]` | Bank Detail | Bank editing and management |
| `invite/` | Invite | Generate invite links |

#### `(auth)` — Authentication

| Route | Page |
|-------|------|
| `login/` | Login form |
| `register/` | Registration form |

#### Other

| Route | Page |
|-------|------|
| `join/` | Invite-based join flow |

### Feature: Voice Interview (`features/voice-interview/`)

| Component/Hook | Purpose |
|----------------|---------|
| `VoiceInterview.tsx` | Full voice interview flow — audio-start, audio-answer, audio-followup, TTS playback, phase management |
| `MicButton.tsx` | Hold-to-talk microphone button with recording state visualization |
| `VoiceWaveform.tsx` | 24-bar audio visualization during recording |
| `useMediaRecorder.ts` | Web MediaRecorder API hook — start/stop recording, blob management |
| `useSpeechRecognition.ts` | Web Speech Recognition API hook — start/stop, interim/final transcripts, error mapping |
| `useSpeechSynthesis.ts` | Web Speech Synthesis API hook — speak, mute/unmute, retry, queue management, localStorage persistence |

### Feature: Anti-Cheat (`features/anti-cheat/`)

See [Section 6](#6-anti-cheat-system) for full details.

| File | Purpose |
|------|---------|
| `useAntiCheat.ts` | Hook: tab switch, blur, copy, paste detection with cooldowns and grace periods |
| `useCameraMonitor.ts` | Hook: camera permission, frame sampling, face detection state machine |
| `CameraMonitor.tsx` | Presentational: video preview, status label (present/absent/unknown) |
| `faceDetector.ts` | Two strategies: NativeFaceDetector API + motion heuristic fallback |
| `AntiCheatIndicator.tsx` | Live integrity score badge (color-coded) |

---

## 6. Anti-Cheat System

The anti-cheat system is a multi-layer proctoring pipeline that monitors candidate behavior during live interviews and enforces integrity policies.

### 6.1 Camera Monitoring Pipeline

```
getUserMedia (camera)
        │
        ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ Video Frame  │────▶│ Downsample   │────▶│ Face Detector│
│ Sampling     │     │ 160x90       │     │              │
│ (500ms)      │     │              │     │              │
└──────────────┘     └──────────────┘     └──────┬───────┘
                                                 │
                                    ┌────────────┴────────────┐
                                    │                         │
                             NativeFaceDetector         MotionHeuristic
                             (Chrome/Edge only)          (fallback)
                                    │                         │
                                    └────────────┬────────────┘
                                                 │
                                                 ▼
                                    ┌──────────────────────┐
                                    │ State Machine         │
                                    │                       │
                                    │ prompting → active    │
                                    │ active ↔ face_lost    │
                                    │ active → denied       │
                                    │ active → unsupported  │
                                    └──────────────────────┘
```

**Face Detection Strategies:**

1. **NativeFaceDetectorStrategy** — Uses the browser's built-in `FaceDetector` API (Chrome/Edge). Returns `present` if faces found, `absent` if none, `unknown` on error.

2. **MotionFaceDetector** (fallback) — Computes frame-over-frame pixel motion. Static scene = absent, changing frames = present. Requires a few frames of history before producing verdicts.

**State Machine:** Face must be absent for **6 consecutive frames** (3 seconds at 500ms intervals) before triggering `face_lost`. This prevents false positives from brief glances at the keyboard.

### 6.2 Input Monitoring

| Event | Detection | Reporting |
|-------|-----------|-----------|
| **Tab switch** | `document.visibilitychange` → `document.hidden` | Reported immediately (one per question) |
| **Window blur** | `window.blur` event | **3-second grace period** — only reported if window stays unfocused for ≥3 seconds |
| **Copy** | `document.copy` event | **Ignored if inside textarea/input** — only external clipboard usage flagged |
| **Paste** | `document.paste` event | **Ignored if inside textarea/input** — only external paste flagged; textarea paste also blocked via `preventDefault()` |
| **Face lost** | Camera face detector (6 consecutive absents) | Reported via `reportFaceLost()` callback |

**Cooldowns:**
- Same event type cannot fire more than once every **10 seconds**
- Backend deduplicates by `reason:question` key — one flag per reason per question

### 6.3 Paste Blocking

The text answer textarea has an `onPaste` handler that calls `event.preventDefault()`, physically preventing paste operations. A visual hint ("Paste disabled — type your answer") appears when paste is attempted. Copy within the textarea is allowed (for normal editing), but the document-level copy listener ignores events from textarea/input elements.

### 6.4 Voice Auto-Stop on Face Loss

When the camera detects face loss during a voice recording:
1. The `blocked` prop flips to `true`
2. A `useEffect` in `VoiceInterview.tsx` detects `blocked && phase === "recording"`
3. `stopListening()` is called to discard the recording blob (not submitted)
4. Phase resets to `"question"` with hint: "Recording paused — face out of view."
5. User must re-position face and start recording again

### 6.5 Integrity Scoring

Events are mapped to severity-weighted reasons:

| Event Type | Reason | Severity | Dedup |
|------------|--------|----------|-------|
| `tab_switch` | `left_interview_window` | -15 | per question |
| `face_lost` | `left_interview_window` | -15 | per question |
| `blur` | `window_blur` | -10 | per question |
| `copy` | `clipboard_usage` | -10 | per question |
| `paste` | `clipboard_usage` | -10 | per question |
| `time_limit_exceeded` | `time_limit_exceeded` | -10 | per question |
| skip | (evaluation `_skipped`) | -5 | per question |

Starting score: **100**. Minimum: **0**.

### 6.6 Hard-Lock Policy

The interview is terminated (locked) when **either** condition is met:

1. **Score-based:** `integrity_score < 50`
2. **Event-count-based:** ≥ 3 `tab_switch` or `face_lost` events across the session

When locked:
- Session `status` set to `"locked"` with `locked_reason`
- All answer/question endpoints return HTTP 403
- Report endpoint still returns data (for locked screen display)
- Frontend renders a "Session Locked — Integrity Policy Violated" screen with score, reason, and link to results

### 6.7 Frontend Lock UX

- **Interview page** (`page.tsx` `ModeSwitch`): Detects `locked` from `useAntiCheat` → replaces room UI with locked screen → "View Report" button
- **Results page** (`results/[sessionId]/page.tsx`): Detects `report.locked` → renders locked screen with score, reason, "View History" and "New Interview" buttons
- **History page** (`history/page.tsx`): `locked` status renders in a red badge

---

## 7. Voice Interview Pipeline

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ Audio Start  │────▶│ Backend:     │────▶│ Gemini Flash │
│ POST         │     │ speech.py    │     │ STT          │
│              │     │ transcribe   │     │              │
└──────────────┘     └──────────────┘     └──────────────┘
        │
        ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ Question     │────▶│ Backend:     │────▶│ Browser      │
│ Display +    │     │ TTS base64   │     │ SpeechSynth  │
│ TTS playback │     │ (returns     │     │ (native)     │
│              │     │  None →      │     │              │
│              │     │  use native) │     │              │
└──────────────┘     └──────────────┘     └──────────────┘
        │
        ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ Hold-to-talk │────▶│ Web Media    │────▶│ POST         │
│ MicButton    │     │ Recorder API │     │ /audio-answer│
│              │     │ blob → base64│     │ multipart    │
└──────────────┘     └──────────────┘     └──────────────┘
        │
        ▼
┌──────────────┐     ┌──────────────┐
│ Follow-up    │────▶│ POST         │
│ or next Q    │     │ /audio-      │
│              │     │ followup     │
└──────────────┘     └──────────────┘
```

**STT Fallback:** On 429/502/503/504 from Gemini API, returns placeholder text ("I am testing the voice interface. What is your next question?") so the interview continues gracefully.

---

## 8. Tech Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| **Backend** | Python | 3.10+ |
| **Web Framework** | FastAPI | ≥0.104.0 |
| **ASGI Server** | Uvicorn | ≥0.24.0 |
| **ORM** | SQLAlchemy | ≥2.0.0 |
| **Validation** | Pydantic v2 | ≥2.5.0 |
| **Database** | SQLite (dev) / Supabase (prod) | — |
| **Auth** | PyJWT + passlib[bcrypt] | ≥2.8.0 / ≥1.7.4 |
| **LLM** | Google Gemini Flash (REST) | gemini-3.5-flash |
| **LLM Fallback** | Ollama | llama3 |
| **HTTP Client** | httpx | ≥0.25.0 |
| **Resume Parsing** | pdfplumber + python-docx | ≥0.10.0 / ≥1.1.0 |
| **Frontend Framework** | Next.js | 14.2.35 |
| **UI Library** | React | 18.x |
| **Language** | TypeScript | 5.x |
| **Styling** | Tailwind CSS | 3.4.1 |
| **Testing (Backend)** | pytest + pytest-cov | ≥7.0.0 / ≥4.0.0 |
| **Testing (Frontend)** | Vitest + Testing Library | 4.1.11 |
| **Property Tests** | fast-check | 4.9.0 |
| **Accessibility Tests** | vitest-axe | 0.1.0 |
| **E2E** | Playwright | ≥1.62.1 |
| **CI** | GitHub Actions | — |

---

## 9. Test Coverage

### Backend (`backend/`)

| Metric | Value |
|--------|-------|
| **Total tests** | 268 |
| **Pass rate** | 100% |
| **Coverage** | 86.50% (gate: 80%) |
| **Test isolation** | Temp SQLite DB per run; dev `interview.db` never touched |
| **LLM mocking** | All LLM calls mocked — no API key needed |

Key test files: `test_api.py`, `test_auth_endpoints.py`, `test_company.py`, `test_custom_api.py`, `test_custom_banks_db.py`, `test_credits.py`, `test_db_crud.py`, `test_invite_flow.py`, `test_integrity.py` (including `TestHardLock`), `test_interview_endpoints.py`, `test_openapi_contract.py`, `test_reports.py`, `test_speech_service.py`, `test_webhooks.py`

### Frontend (`frontend/web/`)

| Metric | Value |
|--------|-------|
| **Total tests** | 135 |
| **Pass rate** | 100% |
| **TypeScript** | `tsc --noEmit` — clean (0 errors) |
| **Production build** | `next build` — passing |
| **Coverage scope** | `src/` (voice-interview + anti-cheat + lib/audio) |

Key test files: `useCameraMonitor.test.ts`, `faceDetector.test.ts`, `CameraMonitor.test.tsx`, `VoiceInterview.test.tsx`, `MicButton.test.tsx`, `VoiceWaveform.test.tsx`, `useSpeechRecognition.test.tsx`, `useSpeechPlayback.test.ts`, `page.test.tsx` (interview room), `page.test.tsx` (setup), `api.test.ts`, `audio.test.ts`, `audio.fastcheck.test.ts`

---

## 10. How It Helps

### For Candidates
- **Practice interviews** in a low-pressure environment with instant AI feedback
- **Voice mode** for natural conversation flow, mimicking real interview conditions
- **Personalized questions** based on resume data — skills, experience level, job titles
- **Detailed reports** with per-question scores, strengths, weaknesses, and recommendations
- **Fair proctoring** — the anti-cheat system is designed to catch genuine cheating while being tolerant of honest behavior (typing, brief focus shifts, looking at keyboard)

### For Hiring Companies
- **Automated screening** — bulk candidate assessment via campaigns
- **Standardized evaluation** — consistent scoring across all candidates using weighted LLM evaluation
- **Cross-candidate comparison** — side-by-side analytics
- **Custom question banks** — upload company-specific questions
- **Webhook integration** — push results to ATS/HRIS systems
- **Integrity enforcement** — locked sessions flag candidates who violate exam policies
- **Invite-based flows** — generate shareable interview links for candidates

### For Organizations
- **Scalable** — LLM evaluation handles unlimited concurrent interviews
- **Configurable** — scoring weights, question counts, verdict thresholds, domain selection all tunable via `config.yaml`
- **Auditable** — full event logging, webhook delivery history, integrity event records
- **Secure** — JWT auth, bcrypt passwords, HMAC-signed webhooks, SSRF protection, CORS restrictions

---

## 11. Deferred & Known Limitations

| Item | Status | Notes |
|------|--------|-------|
| **Supabase hosting** | Deferred | Backend connects via `DATABASE_URL` only; dev runs on local SQLite. Supabase credentials provided by user are not written to code. |
| **Gemini STT quota** | Limited | Google free-tier rate-limits cause 429/503 errors. Graceful fallback to placeholder text is implemented. |
| **Voice blob on auto-stop** | Not submitted | When face loss stops a recording, the blob is discarded (not submitted). User must re-record. |
| **Camera compatibility** | Chrome/Edge only for NativeFaceDetector | Falls back to motion heuristic on Firefox/Safari. |
| **E2E tests** | 2 Playwright specs | Voice interview E2E with fake device media. |
| **Graphify knowledge graph** | Stale | Built Aug 30, does not include recent anti-cheat additions. |

---

## 12. Verification Commands

```powershell
# Backend tests (86.50% coverage)
cd backend
..\venv\Scripts\python -m pytest tests/ -x -q --tb=short

# Frontend tests (135 tests)
cd frontend/web
npx vitest run

# TypeScript check
cd frontend/web
npx tsc --noEmit

# Production build
cd frontend/web
npx next build

# Full frontend verification
cd frontend/web
npm run verify
```

---

*Report generated September 4, 2026.*
