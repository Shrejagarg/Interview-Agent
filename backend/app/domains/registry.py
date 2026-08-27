import logging
from typing import Dict, Optional, List, Any
from .base import BaseDomain

logger = logging.getLogger(__name__)

_DOMAINS: Dict[str, BaseDomain] = {}
_REGISTRY_LOADED = False

DOMAIN_SLUGS = [
    "marketing",
    "software_engineering",
    "finance",
    "hr",
    "sales",
]

_DEFAULT_SCORING_DIMENSIONS = ["relevance", "clarity", "creativity", "communication"]

_DEFAULT_EVALUATION_PROMPT_TEMPLATE = """You are a strict but fair {domain_name} interviewer.

Evaluate the candidate's answer.

Question: {question}
Answer: {answer}

Scoring rules (ALL scores MUST be integers 0-10. NEVER use 0-100):
- If answer is abusive, irrelevant, nonsense, or empty -> very low scores (0-2)
- If answer is generic but somewhat relevant -> medium scores (4-6)
- If answer is strong, structured, and includes useful points/examples -> high scores (7-10)

IMPORTANT: Use ONLY integers between 0 and 10 for ALL scores.
DO NOT use a 0-100 scale.

If the overall_score is below 6, write a 2-3 sentence ideal model answer in "ideal_answer".
If the overall_score is 6 or above, leave "ideal_answer" as an empty string.

Return ONLY valid JSON in this exact format:
{{{dimension_json_keys}
  "overall_score": 0,
  "strengths": ["", ""],
  "weaknesses": ["", ""],
  "ideal_answer": "",
  "follow_up": "",
  "is_serious": true
}}"""


class DynamicDomain(BaseDomain):
    """Domain loaded dynamically from the Supabase database."""

    def __init__(self, data: dict, questions: list[dict] = None,
                 skills: list[dict] = None, job_titles: list[dict] = None):
        self._data = data
        self._questions = questions or []
        self._skills = skills or []
        self._job_titles = job_titles or []

    @property
    def slug(self) -> str:
        return self._data["slug"]

    @property
    def name(self) -> str:
        return self._data["name"]

    @property
    def description(self) -> str:
        return self._data.get("description", "")

    @property
    def topics(self) -> List[str]:
        return self._data.get("topics", [])

    @property
    def scoring_dimensions(self) -> List[str]:
        return self._data.get("scoring_dimensions", _DEFAULT_SCORING_DIMENSIONS)

    def get_questions(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": q["external_id"],
                "topic": q["topic"],
                "difficulty": q["difficulty"],
                "roles": q["roles"],
                "question": q["question_text"],
            }
            for q in self._questions
        ]

    def get_skills(self) -> Dict[str, List[str]]:
        grouped: Dict[str, List[str]] = {}
        for s in self._skills:
            cat = s["category"]
            grouped.setdefault(cat, []).append(s["skill_name"])
        return grouped

    def get_job_titles(self) -> Dict[str, List[str]]:
        grouped: Dict[str, List[str]] = {}
        for jt in self._job_titles:
            level = jt["level"]
            grouped.setdefault(level, []).append(jt["title"])
        return grouped

    def get_evaluation_prompt(self, question: str, answer: str) -> str:
        dimension_keys = ",\n".join(
            f'  "{dim}": 0' for dim in self.scoring_dimensions
        )
        prompt = _DEFAULT_EVALUATION_PROMPT_TEMPLATE.format(
            domain_name=self.name,
            question=question,
            answer=answer,
            dimension_json_keys=dimension_keys,
        )
        return prompt

    def get_recommendation(self, topic: str, score: float) -> str:
        return f"Review fundamentals of {topic} and practice with real scenarios."


def _load_domain_hardcoded(slug: str) -> Optional[BaseDomain]:
    """Fallback: load a domain from the old hardcoded Python module."""
    import importlib
    try:
        module_path = f"backend.app.domains.{slug}"
        module = importlib.import_module(module_path)
        if hasattr(module, "domain"):
            return module.domain
        logger.warning("Domain module '%s' has no 'domain' attribute", slug)
        return None
    except ImportError:
        return None
    except Exception as e:
        logger.error("Error loading domain '%s': %s", slug, e)
        return None


def _load_all():
    """Load all registered domains. Tries Supabase DB first, falls back to hardcoded."""
    global _REGISTRY_LOADED
    if _REGISTRY_LOADED:
        return

    db_loaded = _load_from_db()
    if not db_loaded:
        _load_from_hardcoded()

    _REGISTRY_LOADED = True
    logger.info("Domain registry loaded: %d domains", len(_DOMAINS))


def _load_from_db() -> bool:
    """Attempt to load all domains from Supabase. Returns True if successful."""
    try:
        from backend.app.db.domains import (
            get_domain_db,
            list_domains_db,
            get_domain_questions_db,
            get_domain_skills_db,
            get_domain_job_titles_db,
        )

        domains = list_domains_db()
        if not domains:
            logger.warning("No domains found in database")
            return False

        for data in domains:
            slug = data["slug"]
            domain_id = data["id"]
            questions = get_domain_questions_db(domain_id)
            skills = get_domain_skills_db(domain_id)
            job_titles = get_domain_job_titles_db(domain_id)
            _DOMAINS[slug] = DynamicDomain(data, questions, skills, job_titles)
            logger.info("Loaded domain from DB: %s (%s)", slug, data["name"])

        return True
    except Exception as e:
        logger.warning("Failed to load domains from DB: %s", e)
        return False


def _load_from_hardcoded():
    """Fallback: load domains from hardcoded Python modules."""
    logger.info("Falling back to hardcoded domain modules")
    for slug in DOMAIN_SLUGS:
        domain = _load_domain_hardcoded(slug)
        if domain:
            _DOMAINS[slug] = domain
            logger.info("Loaded domain (hardcoded): %s (%s)", slug, domain.name)


class DomainRegistry:
    """Central registry for accessing domains."""

    def __init__(self):
        _load_all()

    def get(self, slug: str) -> Optional[BaseDomain]:
        return _DOMAINS.get(slug)

    def list_domains(self) -> List[Dict[str, str]]:
        return [
            {"slug": slug, "name": d.name, "description": d.description}
            for slug, d in _DOMAINS.items()
        ]

    def list_slugs(self) -> List[str]:
        return list(_DOMAINS.keys())

    def is_valid(self, slug: str) -> bool:
        return slug in _DOMAINS


_registry: Optional[DomainRegistry] = None


def get_registry() -> DomainRegistry:
    global _registry
    if _registry is None:
        _registry = DomainRegistry()
    return _registry


def reset_registry():
    global _registry, _REGISTRY_LOADED
    _DOMAINS.clear()
    _REGISTRY_LOADED = False
    _registry = None
    try:
        from core import domain_bridge
        domain_bridge._registry = None
    except Exception:
        pass
