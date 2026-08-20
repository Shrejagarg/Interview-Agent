from core import (
    warm_up, check_health, check_model,
    run_interview, generate_report,
    create_interview_state, parse_resume, get_config
)
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
        logger.error("Ollama server is not running. Start it with: ollama serve")
        raise SystemExit(1)

    if not check_model():
        logger.error("Required model '%s' not found. Pull it with: ollama pull %s",
                      cfg["llm"]["model"], cfg["llm"]["model"])
        raise SystemExit(1)

    logger.info("Loading model...")
    warm_up()
    logger.info("Ready!\n")

    resume_data = prompt_resume()

    state = create_interview_state()
    state = run_interview(state, resume_data=resume_data)

    logger.info("\nGenerating full report...\n")
    generate_report(state)


if __name__ == "__main__":
    main()
