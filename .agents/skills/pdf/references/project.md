# This Project — PDF Skill Usage

This vendored skill is Anthropic's production PDF toolkit and targets the Anthropic/Claude API. **In this project it is reference material only.**

## Actual PDF handling here

- Resume parsing lives in `core/resume_parser.py`.
- `.pdf` → text extraction via **`pdfplumber`** (`extract_text_from_pdf`).
- `.docx`/`.doc` → via **`python-docx`** (`extract_text_from_docx`); `.txt` read directly.
- Supported formats are declared in `core/config.py` → `resume.supported_formats` (`[".pdf", ".docx", ".doc", ".txt"]`).

## When to consult this skill

- Understanding form-field extraction, bounding boxes, or creating validation images for PDF output — borrow the *techniques*, not the Anthropic-API scripts.
- If we later need to *generate* PDF reports (e.g., candidate result PDFs), this skill's patterns are a good reference, but the implementation must use an open, non-Claude dependency (e.g., reportlab/weasyprint) and must be added to `requirements.txt`.

## Golden rules

- Do not add Anthropic-API dependencies to `requirements.txt` for this project's PDF work.
- Any new PDF/docx behavior in `core/resume_parser.py` needs parser tests + fixture resumes (see existing `test_resumes/`).