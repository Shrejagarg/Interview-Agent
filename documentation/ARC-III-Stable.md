# ARC III (Stable): Unified Core Architecture

## Overview

This arc transforms the project from two separate codebases (CLI + web backend) into a **single-brain architecture** where the CLI logic becomes the shared core for all interfaces:

- **CLI** — Standalone terminal app (already works)
- **Candidate Frontend** — Practice interviews with full features
- **Company Frontend** — Dashboard, session management, candidate comparison

**Core Principle**: No code duplication. The `core/` package is the single source of truth. Both CLI and web backend import from it.

**Tech Stack**: Python 3.13 (core) + FastAPI (web API) + Next.js 14 (frontends) + Ollama (LLM) + Supabase (Auth)

**Approach**: One phase at a time. Extract core first, then integrate, then build frontends.

---

## Architecture

```
/interview v2/
│
├── core/                        # THE BRAIN (extracted from CLI)
│   ├── __init__.py              # Public API exports
│   ├── config.py                # YAML config loader
│   ├── resume_parser.py         # PDF/DOCX/TXT parsing, 133 skills
│   ├── skills_database.py       # Marketing skills + categories
│   ├── question_engine.py       # 3-source question gen (LLM + bank + templates)
│   ├── question_bank.py         # 60 questions, 14 topics
│   ├── evaluator.py             # 4-dimension scoring, follow-ups, seriousness
│   ├── interviewer.py           # Interview loop orchestration
│   ├── state.py                 # Session state management
│   ├── report.py                # Report generation
│   └── analytics.py             # Skill gaps, trends, recommendations
│
├── main.py                      # CLI entry point (imports from core/)
├── config.yaml                  # Single config file (shared)
├── .asked_questions.json        # Anti-repeat history (shared)
├── sessions/                    # Session JSON files (shared)
│
├── backend/                     # FastAPI web API (imports from core/)
│   ├── app/
│   │   ├── __init__.py
│   │   ├── api/
│   │   │   ├── auth.py          # User auth (dev mock + Supabase)
│   │   │   ├── domains.py       # Domain CRUD
│   │   │   ├── interviews.py    # Interview lifecycle → calls core.*
│   │   │   ├── analytics.py     # Analytics → calls core.*
│   │   │   └── company.py       # Company dashboard
│   │   └── domains/             # Domain definitions
│   └── tests/
│
├── frontend/candidate/          # Candidate UI (Next.js)
├── frontend/company/            # Company UI (Next.js)
│
├── tests/                       # Core tests (163 existing)
│   ├── test_core.py
│   ├── test_resume.py
│   ├── test_question_engine.py
│   ├── test_interview_runner.py
│   └── test_analytics.py
│
└── documentation/
    ├── ARC - II.md
    ├── ARC-III-Stable.md        # This document
    └── CLI-Feature-Audit-Report.md
```

---

## Phase 1: Core Extraction

**Goal**: Move CLI logic to `core/` package without changing behavior.

**Why first**: Everything else depends on this. Must be rock solid before integrating with web.

### 1.1 Create Core Package

**New directory**: `core/`

| File | Source | Changes |
|------|--------|---------|
| `core/__init__.py` | New | Public API exports |
| `core/config.py` | `config.py` | Update path resolution for `config.yaml` |
| `core/resume_parser.py` | `resume_parser.py` | Update import from `skills_database` |
| `core/skills_database.py` | `skills_database.py` | No changes |
| `core/question_engine.py` | `question_engine.py` | Update imports from `config`, `evaluator` |
| `core/question_bank.py` | `question_bank.py` | No changes |
| `core/evaluator.py` | `evaluator.py` | Update import from `config` |
| `core/interviewer.py` | `interviewer.py` | Update imports from `core.*` |
| `core/state.py` | `state.py` | No changes |
| `core/report.py` | `report.py` | Update imports from `state`, `config` |
| `core/analytics.py` | `analytics.py` | Update imports from `config`, `skills_database` |

### 1.2 Update Core `__init__.py`

**File**: `core/__init__.py`

Export all public functions:
```python
from .config import get_config, load_config
from .resume_parser import parse_resume, extract_text
from .skills_database import ALL_SKILLS, SKILL_CATEGORIES, MARKETING_SKILLS
from .question_engine import get_question_set, select_questions
from .question_bank import QUESTION_BANK, TOPICS
from .evaluator import evaluate_main, evaluate_followup, merge, check_health, check_model, warm_up
from .interviewer import run_interview
from .state import create_interview_state, record_answer, update_topic_score, finalize_topics, get_average, export_session
from .report import generate_report
from .analytics import get_session_summary, compare_sessions, skill_gap_analysis, generate_recommendations
```

### 1.3 Update CLI Imports

**File**: `main.py`

Change:
```python
# Old
from config import get_config
from resume_parser import parse_resume
from evaluator import warm_up, check_health, check_model
from interviewer import run_interview
from report import generate_report
from state import create_interview_state

# New
from core import (
    get_config, parse_resume, warm_up, check_health, check_model,
    run_interview, generate_report, create_interview_state
)
```

### 1.4 Update Test Imports

**Files**: `tests/test_*.py`

Change all test imports from:
```python
from config import get_config
from state import create_interview_state
from evaluator import _parse_json, _compute_weighted_score, merge
```

To:
```python
from core import get_config, create_interview_state
from core.evaluator import _parse_json, _compute_weighted_score, merge
```

### 1.5 Fix Path Resolution

**File**: `core/config.py`

Update `load_config()` to find `config.yaml` relative to project root:
```python
def load_config():
    # Was: os.path.dirname(__file__)
    # Now: project root (parent of core/)
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_path = os.path.join(project_root, "config.yaml")
```

**File**: `core/question_engine.py`

Update `.asked_questions.json` path:
```python
# Was: ASKED_QUESTIONS_FILE = ".asked_questions.json"
# Now:
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASKED_QUESTIONS_FILE = os.path.join(project_root, ".asked_questions.json")
```

**File**: `core/state.py`

Update `export_session()` path:
```python
# Was: os.path.join("sessions", filename)
# Now:
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sessions_dir = os.path.join(project_root, "sessions")
```

### 1.6 Verify

Run all 163 CLI tests:
```bash
cd "R:\IMP\interview v2"
python -m pytest test_core.py test_resume.py test_question_engine.py test_interview_runner.py test_analytics.py -v
```

**Must pass**: 163/163

### 1.7 Delete Old Files (After Verification)

Once core tests pass, delete the root-level copies:
- `config.py` → `core/config.py`
- `resume_parser.py` → `core/resume_parser.py`
- `skills_database.py` → `core/skills_database.py`
- `question_engine.py` → `core/question_engine.py`
- `question_bank.py` → `core/question_bank.py`
- `evaluator.py` → `core/evaluator.py`
- `interviewer.py` → `core/interviewer.py`
- `state.py` → `core/state.py`
- `report.py` → `core/report.py`
- `analytics.py` → `core/analytics.py`

**Keep**: `main.py`, `questions.py` (legacy), `config.yaml`, `.asked_questions.json`, `sessions/`

**Estimated**: ~12 files modified, ~100 lines changed

---

## Phase 2: Backend Integration

**Goal**: Web backend uses `core/` modules instead of its own simplified logic.

**Why second**: Backend must be solid before frontends consume it.

### 2.1 Add Resume Upload Endpoint

**File**: `backend/app/api/interviews.py`

New endpoint:
```
POST /api/interviews/parse-resume
  - Accept: multipart/form-data (file upload)
  - Returns: parsed resume data (name, skills, experience, level, quality)
  - Calls: core.resume_parser.parse_resume()
```

### 2.2 Replace Interview Logic with Core

**File**: `backend/app/api/interviews.py`

**Current** (simplified):
```python
def _select_questions(domain, experience_level, count):
    # Simple shuffle from bank
    questions = domain.get_questions()
    random.shuffle(questions)
    return questions[:count]
```

**New** (uses core):
```python
from core import get_question_set, evaluate_main, evaluate_followup, merge

def start_interview(domain_slug, question_count, resume_data, user_id):
    resume = resume_data or {}
    questions = get_question_set(resume, question_count)
    session = {
        "questions": questions,
        "current_index": 0,
        "answers": [],
        "topic_scores": {},
        "user_id": user_id,
        ...
    }
    return session

def submit_answer(session, question_id, answer_text):
    question = session["questions"][session["current_index"]]
    evaluation = evaluate_main(question["question"], answer_text)
    
    # Handle follow-up
    if evaluation.get("follow_up"):
        session["pending_followup"] = evaluation["follow_up"]
        session["pending_evaluation"] = evaluation
        return {"evaluation": evaluation, "follow_up": evaluation["follow_up"]}
    
    # No follow-up → merge and advance
    final_score = merge(evaluation["overall_score"], None)
    update_topic_score(session, question["topic"], final_score)
    record_answer(session, question, answer_text, evaluation, question["topic"], ...)
    session["current_index"] += 1
    return {"evaluation": evaluation, "next_question": get_next_question(session)}
```

### 2.3 Add Follow-Up Endpoint

**File**: `backend/app/api/interviews.py`

New endpoint:
```
POST /api/interviews/{session_id}/followup
  - Accept: { answer_text: string }
  - Returns: { evaluation, next_question }
  - Calls: core.evaluator.evaluate_followup(), core.evaluator.merge()
```

### 2.4 Add Retry Logic for LLM Calls

**File**: `backend/app/api/interviews.py`

Replace single-attempt `_call_llm()` with core's retry logic:
```python
from core.evaluator import _call_llm  # Already has retry with backoff
```

### 2.5 Upgrade Report Generation

**File**: `backend/app/api/interviews.py`

Replace simplified `_compute_session_summary()` with core's full report:
```python
from core.report import generate_report
from core.analytics import generate_recommendations

def get_session_report(session):
    # Generate full report with dimension averages, strengths/weaknesses
    state = session_to_state(session)  # Convert web session to core state format
    generate_report(state)
    recommendations = generate_recommendations(state, session.get("resume_data"))
    return {
        "overall_score": state["average_score"],
        "verdict": state["verdict"],
        "topic_scores": state["topic_scores"],
        "dimension_averages": state["report_summary"]["dimension_averages"],
        "top_strengths": state["report_summary"]["top_strengths"],
        "top_weaknesses": state["report_summary"]["top_weaknesses"],
        "timing": state["report_summary"]["timing"],
        "recommendations": recommendations,
        "answers": state["answers"]
    }
```

### 2.6 Add Anti-Repeat Support

**File**: `backend/app/api/interviews.py`

Use core's anti-repeat system:
```python
from core.question_engine import record_asked, filter_unasked

# When starting interview
for q in questions:
    record_asked(q["id"])

# When selecting questions
unasked = filter_unasked(candidates)
```

### 2.7 Add Weighted Scoring

**File**: `backend/app/api/interviews.py`

Use core's weighted score calculation:
```python
from core.evaluator import _compute_weighted_score

# Instead of using LLM's overall_score directly
weighted_score = _compute_weighted_score(
    evaluation["relevance"],
    evaluation["clarity"],
    evaluation["creativity"],
    evaluation["communication"]
)
evaluation["overall_score"] = weighted_score
```

### 2.8 Verify

Run all backend tests:
```bash
cd "R:\IMP\interview v2"
python -m pytest backend/tests/ -v
```

**Must pass**: 82/82 (existing) + new tests for resume upload, follow-ups, etc.

**Estimated**: ~4 files modified, ~300 lines changed

---

## Phase 3: Candidate Frontend Features

**Goal**: Full feature parity with CLI in the web UI.

**Why third**: Frontend depends on backend being complete.

### 3.1 Resume Upload

**New file**: `frontend/candidate/src/app/interview/resume/page.tsx`

| Feature | Detail |
|---------|--------|
| Upload area | Drag-and-drop or file picker |
| Supported formats | PDF, DOCX, TXT |
| Preview | Show extracted name, skills, experience, quality score |
| Validation | Warn if quality < 30, allow proceed anyway |
| Store | Save parsed data in session for question generation |

**API call**: `POST /api/interviews/parse-resume` (multipart/form-data)

### 3.2 Updated Interview Flow

**File**: `frontend/candidate/src/app/interview/[domain]/[sessionId]/page.tsx`

**Current flow**:
1. Pick domain → Start interview → Answer questions → Get report

**New flow**:
1. Pick domain → Upload resume (optional) → Start interview
2. Answer question → Get evaluation + follow-up (if any)
3. Answer follow-up → Get merged score → Next question
4. Complete all questions → Get detailed report

### 3.3 Follow-Up Question UI

**File**: `frontend/candidate/src/app/interview/[domain]/[sessionId]/page.tsx`

When backend returns `follow_up`:
```
┌─────────────────────────────────────────┐
│ Follow-up Question                      │
│                                         │
│ "Can you elaborate on specific tools    │
│  you use for keyword research?"         │
│                                         │
│ ┌─────────────────────────────────────┐ │
│ │ Your follow-up answer...            │ │
│ │                                     │ │
│ └─────────────────────────────────────┘ │
│                                         │
│ [Submit Follow-Up]                      │
└─────────────────────────────────────────┘
```

**API call**: `POST /api/interviews/{sessionId}/followup`

### 3.4 Detailed Report Page

**File**: `frontend/candidate/src/app/results/[sessionId]/page.tsx`

**Current**: Basic score + topic breakdown

**New**:
```
┌─────────────────────────────────────────┐
│ Interview Report                        │
│                                         │
│ Overall Score: 72/100    Verdict: Strong│
│                                         │
│ ── Dimension Averages ──                │
│ Relevance:     ████████░░ 8.0          │
│ Clarity:       ███████░░░ 7.0          │
│ Creativity:    ██████░░░░ 6.0          │
│ Communication: ████████░░ 8.0          │
│                                         │
│ ── Topic Breakdown ──                   │
│ SEO:        8.5  ★ Strong              │
│ Analytics:  6.2                         │
│ PPC:        4.1  ✗ Weak                │
│                                         │
│ ── Top Strengths ──                     │
│ 1. "Good structured approach" (3x)     │
│ 2. "Mentions specific tools" (2x)      │
│ 3. "Real-world examples" (2x)          │
│                                         │
│ ── Top Weaknesses ──                    │
│ 1. "Lacks specific examples" (2x)      │
│ 2. "Could be more concise" (1x)        │
│                                         │
│ ── Timing ──                            │
│ Total time: 5m 30s                      │
│ Avg answer time: 45s                    │
│ Questions answered: 8/10                │
│                                         │
│ ── Recommendations ──                   │
│ • [HIGH] Review PPC campaign setup     │
│ • [MED]  Practice analytics tools      │
│ • [LOW]  Explore advanced SEO topics   │
│                                         │
│ ── Answers ──                           │
│ Q1 [SEO | easy]... → Score: 8.5        │
│ Q2 [Analytics | medium]... → Score: 6.2│
│ ...                                     │
└─────────────────────────────────────────┘
```

### 3.5 Skill Gap Visualization

**File**: `frontend/candidate/src/app/results/[sessionId]/page.tsx`

If resume was uploaded, show skill gap analysis:
```
┌─────────────────────────────────────────┐
│ Skill Gap Analysis                      │
│                                         │
│ Your Skills → Interview Performance     │
│                                         │
│ SEO           ████████░░ 8.0  ✓ OK     │
│ Google Ads    █████░░░░░ 5.0  ⚠ Gap    │
│ Analytics     ██░░░░░░░░ 2.0  ✗ Critical│
│ Content       ███████░░░ 7.0  ✓ OK     │
│ Social Media  (not tested)             │
│                                         │
│ Recommendations based on your resume:   │
│ • [HIGH] Practice Google Ads campaigns  │
│ • [HIGH] Study analytics tools          │
└─────────────────────────────────────────┘
```

**API call**: `GET /api/analytics/recommendations/{sessionId}` (includes skill gap)

### 3.6 Timing Display

**File**: `frontend/candidate/src/app/interview/[domain]/[sessionId]/page.tsx`

Show timer during interview:
```
┌─────────────────────────────────────────┐
│ Question 3/10  |  Topic: SEO  |  Easy  │
│                                         │
│ How would you approach keyword research │
│ for a new website?                      │
│                                         │
│ ┌─────────────────────────────────────┐ │
│ │ Type your answer...                 │ │
│ │                                     │ │
│ └─────────────────────────────────────┘ │
│                                         │
│ Time: 0:45  |  [Submit Answer]          │
└─────────────────────────────────────────┘
```

Track `answer_time_seconds` by recording start time on question load, submit time on answer.

**Estimated**: ~8 files modified/created, ~600 lines

---

## Phase 4: Company Frontend

**Goal**: Company dashboard with full analytics from core.

**Why fourth**: Depends on backend integration being complete.

### 4.1 Company Frontend App

**New directory**: `frontend/company/`

Same structure as ARC-II Phase 3, but now with full core integration.

### 4.2 Enhanced Dashboard

**File**: `frontend/company/src/app/page.tsx`

**New features**:
- Skill gap heatmap across all candidates
- Trend chart (average scores over time)
- Top/bottom performers list
- Domain performance breakdown

### 4.3 Session Detail with Full Report

**File**: `frontend/company/src/app/sessions/[sessionId]/page.tsx`

Same as candidate report but with company view:
- Candidate info (name, email, resume skills)
- Full dimension averages
- Topic scores with charts
- All answers with evaluations
- Skill gap analysis
- Recommendations
- Timing analysis

### 4.4 Candidate Comparison with Skill Gaps

**File**: `frontend/company/src/app/compare/page.tsx`

Enhanced comparison:
- Side-by-side dimension averages
- Topic score radar chart
- Skill gap comparison (if resumes uploaded)
- Strengths/weaknesses overlap analysis

### 4.5 Candidate Profile Page

**New file**: `frontend/company/src/app/candidates/[candidateId]/page.tsx`

Aggregated view of a candidate across all interviews:
- Best scores per domain
- Skill progression over time
- Resume skills vs performance
- All sessions list

**Estimated**: ~15 files, ~900 lines

---

## Phase 5: Integration & Verification

**Goal**: Make sure everything works together end-to-end.

### 5.1 CLI Verification

Test CLI still works after core extraction:
```bash
cd "R:\IMP\interview v2"
python main.py
# Upload resume → Answer questions → Get report → Verify sessions/ export
```

### 5.2 Backend API Tests

Run all backend tests:
```bash
python -m pytest backend/tests/ -v
```

Add new tests for:
- Resume upload endpoint
- Follow-up flow
- Weighted scoring
- Anti-repeat

### 5.3 Core Tests

Run all core tests:
```bash
python -m pytest test_core.py test_resume.py test_question_engine.py test_interview_runner.py test_analytics.py -v
```

**Must pass**: 163/163

### 5.4 End-to-End Flow Test

**Candidate flow**:
1. Register → Login → Upload resume → Pick domain → Start interview
2. Answer questions → Get follow-ups → Complete interview → View detailed report
3. View skill gap analysis → View recommendations

**Company flow**:
1. Register → Login → View dashboard → See aggregate stats
2. View sessions → See candidate reports with full details
3. Compare candidates → View skill gaps → Make decisions

### 5.5 Cross-Interface Verification

- Candidate completes interview → Session appears in company dashboard
- Company can view candidate's full answers, scores, skill gaps
- CLI exported sessions → Web backend can read them
- Anti-repeat works across CLI and web

### 5.6 Git Tagging

After all tests pass:
```bash
git add .
git commit -m "feat: ARC III complete — unified core architecture"
git tag v3.0.0-arc3-stable
```

**Estimated**: ~5 files, ~200 lines (mostly tests)

---

## File Change Summary

| Phase | New Files | Modified Files | Lines (est.) |
|-------|-----------|---------------|-------------|
| Phase 1 (Core Extraction) | `core/` directory (11 files) | `main.py`, 5 test files | ~100 |
| Phase 2 (Backend Integration) | - | `interviews.py`, `analytics.py` | ~300 |
| Phase 3 (Candidate Frontend) | 2-3 new pages | 3-4 existing pages | ~600 |
| Phase 4 (Company Frontend) | ~15 files | - | ~900 |
| Phase 5 (Integration) | - | Test files | ~200 |
| **Total** | **~30 new** | **~15 modified** | **~2100** |

---

## Execution Order

```
Phase 1: Core Extraction
    ↓
Phase 2: Backend Integration
    ↓
Phase 3: Candidate Frontend Features
    ↓
Phase 4: Company Frontend
    ↓
Phase 5: Integration & Verification
```

**Critical path**: Phase 1 → Phase 2 → Phase 3/4 (parallel) → Phase 5

---

## What is NOT in This Phase

- Docker/deployment optimization
- Custom question banks for companies (next arc)
- Supabase data persistence (sessions stay in-memory for now)
- PDF export / share results
- Real-time features (WebSocket, live updates)
- Advanced UI/polish (design later)
- Multi-language support
- Rate limiting / abuse prevention
- Cost tracking for LLM usage

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Core extraction breaks CLI | Run all 163 tests after extraction |
| Backend integration breaks API | Run all 82 tests after integration |
| Path resolution issues | Use `__file__` relative paths consistently |
| Config conflicts | Single `config.yaml` shared by all |
| Session format mismatch | Define clear session dict schema |
| Anti-repeat race conditions | File locking for concurrent web sessions |

---

## Success Criteria

- [ ] CLI works standalone with `python main.py`
- [ ] All 163 core tests pass
- [ ] All 82 backend tests pass
- [ ] Candidate frontend: resume upload, follow-ups, detailed reports
- [ ] Company frontend: dashboard, sessions, candidates, compare
- [ ] Cross-interface: CLI sessions visible in web, anti-repeat works across all
- [ ] No code duplication between CLI and web backend
