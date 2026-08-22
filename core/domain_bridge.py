"""
Domain bridge: provides core/ with access to the domain registry
from backend/app/domains/ without creating circular imports.

The bridge is lazy-loaded — it only imports the backend registry
when first accessed, so core/ still works standalone if backend/
is not present (falls back to marketing defaults).
"""

from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger(__name__)

_registry = None


def get_domain_registry():
    global _registry
    if _registry is None:
        try:
            from backend.app.domains.registry import get_registry
            _registry = get_registry()
            logger.debug("Domain registry loaded into core bridge")
        except ImportError:
            logger.warning(
                "backend/ not available — core/ will use marketing defaults only"
            )
            _registry = None
    return _registry


def get_domain(slug: str):
    registry = get_domain_registry()
    if registry is None:
        return None
    return registry.get(slug)


def get_domain_topics(slug: str) -> List[str]:
    domain = get_domain(slug)
    if domain:
        return domain.topics
    from core.skills_database import MARKETING_SKILLS
    return list(MARKETING_SKILLS.keys())


def get_domain_scoring_dimensions(slug: str) -> List[str]:
    domain = get_domain(slug)
    if domain:
        return domain.scoring_dimensions
    return ["relevance", "clarity", "creativity", "communication"]


def get_domain_evaluation_prompt(slug: str, question: str, answer: str) -> Optional[str]:
    domain = get_domain(slug)
    if domain:
        return domain.get_evaluation_prompt(question, answer)
    return None


def get_domain_questions(slug: str) -> List[Dict[str, Any]]:
    domain = get_domain(slug)
    if domain:
        return domain.get_questions()
    from core.question_bank import QUESTION_BANK
    return QUESTION_BANK


def get_domain_skills(slug: str) -> Dict[str, List[str]]:
    domain = get_domain(slug)
    if domain:
        return domain.get_skills()
    from core.skills_database import MARKETING_SKILLS
    return MARKETING_SKILLS


def get_domain_recommendation(slug: str, topic: str, score: float) -> str:
    domain = get_domain(slug)
    if domain:
        return domain.get_recommendation(topic, score)
    from core.analytics import _get_topic_recommendation
    return _get_topic_recommendation(topic, score)


def list_available_domains() -> List[Dict[str, str]]:
    registry = get_domain_registry()
    if registry:
        return registry.list_domains()
    return [{"slug": "marketing", "name": "Marketing", "description": "Marketing interview questions"}]
