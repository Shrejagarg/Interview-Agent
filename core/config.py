import yaml
import os
import logging

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logger = logging.getLogger(__name__)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(PROJECT_ROOT, "config.yaml")

DEFAULT_CONFIG = {
    "llm": {
        "provider": "ollama",
        "model": "llama3",
        "timeout": 60,
        "keep_alive": "10m",
        "max_retries": 3,
        "retry_delay": 2
    },
    "scoring": {
        "relevance_weight": 0.3,
        "clarity_weight": 0.25,
        "creativity_weight": 0.25,
        "communication_weight": 0.2
    },
    "merge": {
        "main_weight": 0.7,
        "followup_weight": 0.3
    },
    "interview": {
        "max_followups_per_question": 1,
        "min_answer_length": 5,
        "question_count": 5,
        "show_feedback": True,
        "show_score_after_answer": True
    },
    "verdicts": {
        "strong_threshold": 7,
        "average_threshold": 5
    },
    "resume": {
        "supported_formats": [".pdf", ".docx", ".doc", ".txt"],
        "min_quality_score": 30,
        "required_sections": ["contact", "skills", "experience"],
        "quality_weights": {
            "contact_info": 15,
            "skills_high": 25,
            "skills_mid": 15,
            "skills_low": 8,
            "experience_years": 20,
            "experience_titles": 12,
            "education": 20,
            "name": 10,
            "length_high": 10,
            "length_mid": 6,
            "skill_thresholds": {"high": 5, "mid": 3},
            "length_thresholds": {"high": 150, "mid": 80}
        }
    },
    "question_engine": {
        "use_llm_generation": True,
        "randomize_order": True,
        "anti_repeat_window": 50,
        "topic_coverage_weight": 0.3,
        "difficulty_distribution": {
            "fresher": {"easy": 0.7, "medium": 0.3, "hard": 0.0},
            "mid": {"easy": 0.2, "medium": 0.6, "hard": 0.2},
            "senior": {"easy": 0.0, "medium": 0.4, "hard": 0.6},
            "unknown": {"easy": 0.3, "medium": 0.5, "hard": 0.2}
        }
    },
    "logging": {
        "level": "INFO"
    }
}


def load_config():
    if not os.path.exists(CONFIG_PATH):
        logger.warning("config.yaml not found at %s, using defaults", CONFIG_PATH)
        return DEFAULT_CONFIG.copy()

    try:
        with open(CONFIG_PATH, "r") as f:
            config = yaml.safe_load(f)
    except yaml.YAMLError as e:
        logger.error("config.yaml is malformed: %s, using defaults", e)
        return DEFAULT_CONFIG.copy()

    if not isinstance(config, dict):
        logger.warning("config.yaml root is not a dictionary, using defaults")
        return DEFAULT_CONFIG.copy()

    for key, default in DEFAULT_CONFIG.items():
        if key not in config:
            logger.warning("Missing '%s' in config.yaml, using default", key)
            config[key] = default
        elif isinstance(default, dict):
            for sub_key, sub_default in default.items():
                if sub_key not in config[key]:
                    logger.warning("Missing '%s.%s' in config.yaml, using default", key, sub_key)
                    config[key][sub_key] = sub_default

    return config


_config = None


def get_config():
    global _config
    if _config is None:
        _config = load_config()
    return _config
