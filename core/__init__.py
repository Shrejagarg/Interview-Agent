"""
Interview Simulator Core Package

Single brain for CLI, Candidate Frontend, and Company Frontend.
All business logic lives here — no duplication.
"""

# Config
from .config import get_config, load_config, DEFAULT_CONFIG

# Resume
from .resume_parser import (
    parse_resume, extract_text, extract_contact, extract_name,
    extract_skills, extract_experience, extract_education,
    detect_experience_level, score_resume_quality, check_required_sections
)

# Skills
from .skills_database import ALL_SKILLS, SKILL_CATEGORIES, MARKETING_SKILLS

# Questions
from .question_engine import (
    get_question_set, select_questions, build_personalized_questions,
    generate_llm_questions, filter_by_role, filter_unasked,
    shuffle_questions, calculate_topic_coverage, select_by_difficulty_pool,
    get_difficulty_distribution, record_asked, load_asked_history,
    save_asked_history, filter_by_difficulty, ANTI_REPEAT_FILE,
    _parse_json_response, AdaptiveDifficultyManager, deduplicate_by_topic,
    semantic_overlap_score
)
from .question_bank import QUESTION_BANK, TOPICS, DIFFICULTY_LEVELS

# Evaluator
from .evaluator import (
    evaluate_main, evaluate_followup, merge, _parse_json,
    _compute_weighted_score, _normalize_scores, _call_llm, check_health,
    check_model, warm_up, pre_screen_answer, PERSONA_PROMPTS
)

# Interviewer
from .interviewer import (
    run_interview, validate_answer, _print_feedback, _print_progress,
    _handle_answer_skip, _handle_evaluation_error, _handle_followup, _print_verdict
)

# State
from .state import (
    create_interview_state, record_answer, update_topic_score,
    add_warning, add_seriousness_flag, finalize_topics, get_average,
    get_integrity_score, export_session
)

# Report
from .report import generate_report

# Analytics
from .analytics import (
    get_session_summary, compare_sessions, skill_gap_analysis,
    generate_recommendations, load_session, load_all_sessions,
    ascii_bar_chart, ascii_comparison_chart, export_text_report,
    export_structured_summary, compare_candidates, SESSIONS_DIR
)

# Domain Bridge
from .domain_bridge import (
    get_domain, get_domain_topics, get_domain_scoring_dimensions,
    get_domain_evaluation_prompt, get_domain_questions, get_domain_skills,
    get_domain_recommendation, list_available_domains
)

# User Profile
from .user_profile import (
    get_user_sessions, calculate_learning_curve,
    get_question_history, generate_study_path
)
