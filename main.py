from core import (
    warm_up, check_health, check_model,
    run_interview, generate_report,
    create_interview_state, parse_resume, get_config
)
from core.domain_bridge import list_available_domains
from core.user_profile import calculate_learning_curve
import logging
import sys
import os


def setup_logging(cfg):
    log_level = cfg["logging"]["level"]
    level = getattr(logging, log_level)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(logging.Formatter("%(message)s"))

    file_handler = logging.FileHandler("interview.log", encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    ))

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.addHandler(console_handler)
    root.addHandler(file_handler)


def prompt_resume():
    logger = logging.getLogger(__name__)
    logger.info("")
    logger.info("Do you want to upload a resume? (y/n)")
    choice = input("> ").strip().lower()

    if choice not in ("y", "yes"):
        return None

    logger.info("Enter resume file path (pdf, docx, txt):")
    path = input("> ").strip().strip('"').strip("'")

    if not path or not os.path.exists(path):
        logger.info("File not found: %s", path)
        return None

    resume_data = parse_resume(path)
    if not resume_data:
        logger.info("Failed to parse resume. Continuing without it.")
        return None

    name = resume_data.get("name", "Unknown")
    level = resume_data.get("experience_level", "unknown")
    quality = resume_data.get("quality", {}).get("score", 0)
    skills_count = resume_data.get("skills", {}).get("skill_count", 0)

    logger.info("")
    logger.info("  Resume loaded: %s", name)
    logger.info("  Experience level: %s", level)
    logger.info("  Skills found: %d", skills_count)
    logger.info("  Quality score: %d/100", quality)

    meets = resume_data.get("quality", {}).get("meets_minimum", True)
    if not meets:
        logger.info("  Warning: Resume quality is below recommended threshold.")
        sections = resume_data.get("sections_check", {})
        missing = sections.get("missing", [])
        if missing:
            logger.info("  Missing sections: %s", ", ".join(missing))

    return resume_data


def main():
    cfg = get_config()
    setup_logging(cfg)

    logger = logging.getLogger(__name__)

    if not check_health():
        logger.error("LLM backend is not available. Check your provider settings and API key in config.yaml")
        raise SystemExit(1)

    if not check_model():
        logger.error("Required model '%s' not found. Pull it with: ollama pull %s",
                      cfg["llm"]["model"], cfg["llm"]["model"])
        raise SystemExit(1)

    logger.info("Loading model...")
    warm_up()
    logger.info("Ready!\n")

    user_id = input("Enter your user ID (or press Enter for anonymous): ").strip() or "anonymous"

    domains = list_available_domains()
    if len(domains) == 1:
        domain_slug = "marketing"
        logger.info("Domain: Marketing")
    else:
        logger.info("Available domains:")
        for i, d in enumerate(domains):
            logger.info("  [%d] %s — %s", i + 1, d["name"], d["description"])

        choice = input("\nSelect domain (number): ").strip()
        try:
            domain_slug = domains[int(choice) - 1]["slug"]
        except (ValueError, IndexError):
            domain_slug = "marketing"
            logger.info("Invalid choice, defaulting to Marketing")
        logger.info("Domain: %s\n", domain_slug)

    logger.info("Select mode:")
    logger.info("  [1] Mock Interview — Full scoring, time limits, prescreening")
    logger.info("  [2] Practice (Warmup) — Coaching tips, no strict limits")
    mode_choice = input("\nMode (number): ").strip()
    mode = "warmup" if mode_choice == "2" else "mock"
    logger.info("Mode: %s\n", mode)

    resume_data = prompt_resume()

    role_context = {}
    logger.info("Do you want to simulate a company pre-screening? (y/n)")
    if input("> ").strip().lower() in ("y", "yes"):
        role_context["role_name"] = input("  Role Title (e.g. Senior Dev): ").strip()
        role_context["company_name"] = input("  Company Name: ").strip()
        try:
            thresh = float(input("  Pass threshold (0-10, default 7.0): ").strip() or "7.0")
            role_context["pass_threshold"] = thresh
        except ValueError:
            role_context["pass_threshold"] = 7.0
        try:
            limit = int(input("  Max answer time in seconds (default 120): ").strip() or "120")
            role_context["max_answer_time_seconds"] = limit
        except ValueError:
            role_context["max_answer_time_seconds"] = 120
        logger.info("  Pre-screening ON — threshold: %s, time limit: %ss",
                     role_context["pass_threshold"], role_context["max_answer_time_seconds"])

    state = create_interview_state(domain_slug=domain_slug, role_context=role_context, user_id=user_id, mode=mode)
    state = run_interview(state, resume_data=resume_data, domain_slug=domain_slug)

    logger.info("\nGenerating full report...\n")
    generate_report(state)

    if user_id != "anonymous":
        curve = calculate_learning_curve(user_id, domain_slug)
        if curve.get("overall"):
            logger.info("\n--- LEARNING CURVE ---")
            logger.info("  Sessions completed: %d", len(curve["overall"]))
            recent = curve["overall"][-5:]
            logger.info("  Recent averages: %s", " -> ".join(f"{s:.2f}" for s in recent))
            if len(recent) >= 2:
                trend = "improving" if recent[-1] > recent[0] else "declining" if recent[-1] < recent[0] else "stable"
                logger.info("  Trend: %s", trend)
            logger.info("")


if __name__ == "__main__":
    main()
