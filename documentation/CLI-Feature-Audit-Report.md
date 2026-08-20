# CLI Feature Audit Report

**Date:** 2026-08-20
**Branch:** phase1-backend-refactor
**Status:** 163/163 CLI tests passing, 82/82 backend tests passing

---

## Executive Summary

The CLI app has **significantly more features** than the web backend. The web backend is missing ~23 major features and has degraded versions of 4 more. The CLI app is production-ready; the web backend is a thin wrapper missing most of the CLI's intelligence.

---

## CLI Feature Test Results

### 1. Config System (`config.py` + `config.yaml`) — WORKING

- All 8 sections load correctly (`llm`, `scoring`, `merge`, `interview`, `verdicts`, `resume`, `question_engine`, `logging`)
- Scoring weights sum to 1.0 (relevance: 0.30, clarity: 0.25, creativity: 0.25, communication: 0.20)
- Merge weights sum to 1.0 (main: 0.70, followup: 0.30)
- Difficulty distributions correct per level (fresher: 0.7/0.3/0.0, mid: 0.2/0.6/0.2, senior: 0.0/0.4/0.6)
- Resume quality threshold (30/100) is reasonable

**Issues:** One-level-deep merge limitation (sub-keys in nested dicts not back-filled).

### 2. Resume Parser (`resume_parser.py`) — WORKING

- PDF/DOCX/TXT extraction via pdfplumber, python-docx, plain text
- 133 marketing skills across 8 categories (digital_marketing, social_media, content, analytics_tools, branding, tools_platforms, strategy, pr_communication)
- Name/contact/skills/experience/education extraction via regex
- Experience level detection (fresher/mid/senior) from years + job title keywords
- Quality scoring (0-100) with configurable weights

**Issues:**
- `.doc` format silently fails (python-docx can't read legacy `.doc`)
- Names with hyphens/apostrophes/periods rejected
- Phone regex overly broad
- `len(words) < 1` is dead code

### 3. Question Engine (`question_engine.py`) — WORKING

- 60 questions across 14 topics in `question_bank.py`
- Role-based filtering (fresher/mid/senior)
- Anti-repeat system (sliding window of 50, persisted to `.asked_questions.json`)
- Difficulty pool selection per level with ratio-based allocation
- LLM-generated questions (needs Ollama) — personalized from resume data
- Template-based personalization (8 templates with `{skill}`, `{title}`, `{years}`, `{category}` placeholders)

**Issues:**
- LLM questions bypass difficulty distribution enforcement
- Anti-repeat only covers bank questions (LLM/template questions get unique IDs)
- LLM question IDs not content-hashed (duplicate content possible across runs)
- Race conditions on `.asked_questions.json` with concurrent sessions

### 4. Evaluator (`evaluator.py`) — WORKING

- 4-dimension scoring (relevance/clarity/creativity/communication) on 0-10 scale
- Weighted score calculation from config weights
- Follow-up question evaluation with separate prompt
- Score merging (70% main + 30% followup)
- Seriousness detection via LLM `is_serious` flag
- Retry logic with exponential backoff (3 attempts)

**Issues:**
- Falls back to score=1 when LLM down (too harsh)
- `is_serious` defaults to False on failure (unfairly flags candidates)
- JSON parser less robust than question engine's parser

### 5. Interview Loop (`interviewer.py`) — WORKING

- Full interview flow: question → answer → evaluate → feedback → next
- Ctrl+C graceful exit with partial session save
- Answer validation (min 5 chars)
- Follow-up questioning (max 1 per question despite config)
- Per-question feedback with dimension breakdown

**Issues:**
- Topic scores overwritten (not averaged) — if two questions share a topic, only the last score is kept
- `_handle_followup` only asks 1 follow-up regardless of `max_followups` config
- No `try/finally` for session export on unexpected exceptions
- `_avg` private key leaks into exported JSON

### 6. State Management (`state.py`) — WORKING

- Create/record/update/finalize/export lifecycle
- Topic classification: strong (>=7), weak (<=5)
- Session export to `sessions/session_{id}.json`

**Issues:**
- Session ID collision risk (second-level granularity)
- No atomic write (temp + rename pattern)

### 7. Report Generation (`report.py`) — WORKING

- Dimension averages across all valid answers
- Top 3 strengths/weaknesses with frequency counts
- Timing analysis (total/avg answer time, eval time)
- Seriousness percentage and warnings

**Issues:**
- `generate_report()` never called from `run_interview` — must be called separately
- Visual report uses `logger.info()` (invisible at non-INFO log levels)
- `_get_strengths_weaknesses` doesn't filter `_parse_error` evaluations

### 8. Analytics (`analytics.py`) — WORKING

- Session summary and comparison with trend detection
- Skill gap analysis (maps resume skills → interview performance → gaps)
- Prioritized recommendations (high/medium/low)
- ASCII bar charts and comparison charts
- Text and structured export
- Candidate comparison with rankings

**Issues:**
- Trend analysis only compares first and last session
- Skill category names don't align with question topic names
- `compare_candidates` chart only uses first two candidates

---

## Web Backend vs CLI — Feature Gap Summary

| Category | CLI Has | Web Has | Gap |
|----------|---------|---------|-----|
| **Resume Parsing** | Full (PDF/DOCX/TXT, 133 skills, quality scoring) | None | 100% missing |
| **Question Engine** | 3-source generation (LLM + bank + templates), anti-repeat, role filtering | Simple shuffle from bank | 80% missing |
| **LLM Integration** | Retry logic, health checks, warm-up | Single attempt, no retries | 60% missing |
| **Evaluation** | Weighted scoring, follow-ups, seriousness detection | Raw LLM score, no follow-ups | 70% missing |
| **Reporting** | Dimension averages, strengths/weaknesses, timing, seriousness | Basic JSON | 80% missing |
| **Analytics** | Skill gaps, prioritized recs, trends, candidate comparison | Basic sessions + compare | 70% missing |
| **Configuration** | Full YAML config (scoring, merge, thresholds, resume, engine) | Env vars only | 90% missing |

---

## Web Backend — Detailed Feature Gaps

### A. Resume Parsing — COMPLETELY MISSING

| Feature | CLI | Web Backend |
|---------|-----|-------------|
| PDF/DOCX/TXT text extraction | `resume_parser.py`: pdfplumber, python-docx, plain text | None |
| Name extraction from resume | `extract_name()` with header/noise filtering | None |
| Contact extraction (email, phone) | `extract_contact()` via regex | None |
| Skill extraction against 100+ skill database | `extract_skills()` matches against `ALL_SKILLS` | None |
| Experience extraction (years + job titles) | `extract_experience()` with regex patterns | None |
| Education extraction | `extract_education()` | None |
| Experience level detection from titles | `detect_experience_level()` checks job title keywords | Web only uses `years_experience` |
| Resume quality scoring | `score_resume_quality()` with configurable weights | None |
| Required sections check | `check_required_sections()` | None |
| Minimum quality threshold warning | Compares quality score against config | None |

### B. Question Engine — SEVERELY SIMPLIFIED

| Feature | CLI | Web Backend |
|---------|-----|-------------|
| Role-based question filtering | `filter_by_role()` — questions have `roles` list | None |
| Anti-repeat / previously-asked filtering | `filter_unasked()` — tracks in `.asked_questions.json` | None |
| Difficulty pool selection | `select_by_difficulty_pool()` — ratio-based allocation | Shuffles and takes first N |
| LLM-generated personalized questions | `generate_llm_questions()` from resume data | None |
| Template-based personalized questions | `build_personalized_questions()` — 8 templates | None |
| Question source tracking | `source` field: "llm", "bank", "template" | None |
| Topic coverage calculation | `calculate_topic_coverage()` | None |

### C. LLM Calls — NO RETRY, NO HEALTH CHECK

| Feature | CLI | Web Backend |
|---------|-----|-------------|
| Retry logic | Up to 3 attempts with exponential backoff | Single attempt |
| Health check on startup | `check_health()` verifies Ollama reachable | None |
| Model availability check | `check_model()` verifies model downloaded | None |
| Warm-up call | `warm_up()` pre-loads model | None |

### D. Evaluation — NO WEIGHTED SCORING, NO FOLLOW-UPS

| Feature | CLI | Web Backend |
|---------|-----|-------------|
| Weighted overall score | Configurable weights (0.3/0.25/0.25/0.2) | Uses LLM's raw `overall_score` |
| Follow-up questions | Ask, evaluate, merge (70/30) | `follow_up` field ignored |
| Seriousness flagging | Tracks and reports unusious answers | `is_serious` stored but unused |
| Warning accumulation | Collects warnings (skips, errors) | None |
| Evaluation error handling | Records `_evaluation_error` / `_parse_error` | Silent fallback |

### E. Scoring and Verdict — DIFFERENT SCALES AND LOGIC

| Feature | CLI | Web Backend |
|---------|-----|-------------|
| Score scale | 0-10 | 0-100 |
| Verdict thresholds | Configurable: strong >= 7, average >= 5 | Hardcoded: >= 75 strong, >= 50 moderate |
| Verdict values | "Strong", "Average", "Needs Improvement" | "strong", "moderate", "weak", "very_weak" |
| Topic finalization | `finalize_topics()` classifies strong/weak | None |
| Skipped question counting | Counts `_skipped` + `_evaluation_error` | None |

### F. Reporting — MISSING MANY SECTIONS

| Feature | CLI | Web Backend |
|---------|-----|-------------|
| Dimension averages | Averages relevance/clarity/creativity/communication | None |
| Top strengths (aggregated) | Top 3 with frequency counts | None |
| Top weaknesses (aggregated) | Top 3 with frequency counts | None |
| Timing analysis | Total/avg answer time, eval time | None |
| Seriousness report | Count and percentage | None |
| Warnings section | All accumulated warnings | None |
| Text report export | `export_text_report()` | None |
| Session file persistence | Writes JSON to `sessions/` | In-memory only |

### G. Analytics — MISSING MAJOR FEATURES

| Feature | CLI | Web Backend |
|---------|-----|-------------|
| Skill gap analysis | Maps resume skills → performance → gaps | None |
| Prioritized recommendations | High/medium/low priority, topic-specific tips | Basic per-topic strings |
| Overall trend detection | "improving", "declining", "stable" | None |
| Best/worst session | Identifies best and worst | None |
| Candidate comparison | Rankings, topic bests, comparison charts | Not available |

### H. Configuration System — MISSING

| Feature | CLI | Web Backend |
|---------|-----|-------------|
| YAML-based config | `config.yaml` with full defaults | Env vars only |
| Configurable scoring weights | `relevance_weight: 0.3`, etc. | None |
| Configurable merge weights | `main_weight: 0.7`, etc. | None |
| Configurable question engine | `use_llm_generation`, `anti_repeat_window`, etc. | None |
| Configurable verdict thresholds | `strong_threshold: 7`, etc. | None |
| Configurable interview settings | `max_followups`, `min_answer_length`, etc. | None |
| Configurable resume settings | `supported_formats`, `min_quality_score`, etc. | None |
| Configurable LLM settings | `timeout`, `keep_alive`, `max_retries`, etc. | Only `MODEL_NAME` env var |

---

## What's Actually Broken vs Just Missing

### Actually Broken (Bugs):

1. **Topic score overwrite** — `update_topic_score` overwrites instead of averaging; if two questions share a topic, only the last score is kept
2. **`_handle_followup` only asks 1** — Config `max_followups_per_question` value ignored
3. **`report_summary` never populated** — `generate_report()` not called from `run_interview`
4. **Seriousness defaults to False** on LLM failure — unfairly flags all candidates as unserious
5. **Score=1 fallback** — Too harsh when LLM is down; should be more lenient
6. **Session ID collision** — Second-level granularity means two sessions in the same second overwrite each other

### Missing but Critical:

1. Resume upload/parsing
2. Personalized question generation (LLM + template)
3. Follow-up question flow
4. Retry logic for LLM calls
5. Weighted scoring recalculation
6. Dimension averages in reports
7. Session persistence
8. Skill gap analysis
9. YAML configuration
10. Anti-repeat system
11. Role-based question filtering
12. Seriousness tracking/reporting
13. Timing analysis

---

## Recommendation

The CLI app is **production-ready** with 163 passing tests. The web backend is a **thin wrapper** missing most of the CLI's intelligence.

**Options:**
1. **Port CLI features to web** — Copy `resume_parser.py`, `question_engine.py`, `evaluator.py`, `analytics.py` logic into the FastAPI backend
2. **Import CLI modules directly** — Web backend imports from the root-level Python files
3. **Keep separate** — CLI for rich local experience, web for basic remote access
