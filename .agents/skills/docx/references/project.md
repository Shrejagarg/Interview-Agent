# This Project — DOCX Skill Usage

This vendored skill is Anthropic's production Word-document toolkit and targets the Anthropic/Claude API. **In this project it is reference material only.**

## Actual DOCX handling here

- Resume parsing lives in `core/resume_parser.py`.
- `.docx`/`.doc` → text extraction via **`python-docx`** (`extract_text_from_docx`); PDFs via `pdfplumber`; plain `.txt` read directly.
- Supported formats: `core/config.py` → `resume.supported_formats` (`[".pdf", ".docx", ".doc", ".txt"]`).

## When to consult this skill

- Improving extraction robustness (merge_runs, tracked-changes handling, validating produced docs) — borrow the *techniques*.
- If we later need to *generate/resume-style Word deliverables* (e.g., exportable interview reports), use this skill's patterns as a guide, implemented with `python-docx` (already a dependency).

## Golden rules

- Do not add Anthropic-API dependencies to `requirements.txt` for DOCX work.
- Any change to `core/resume_parser.py` extractors requires parser tests + fixture resumes (see existing `test_resumes/`).