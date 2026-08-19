"""Domain endpoints — list and query available interview domains"""

from fastapi import APIRouter, HTTPException
from backend.app.domains import get_registry

router = APIRouter()


@router.get("")
def list_domains():
    """List all available interview domains."""
    registry = get_registry()
    return {"domains": registry.list_domains()}


@router.get("/{slug}")
def get_domain(slug: str):
    """Get details about a specific domain."""
    registry = get_registry()
    domain = registry.get(slug)
    if not domain:
        raise HTTPException(status_code=404, detail=f"Domain '{slug}' not found")

    return {
        "slug": domain.slug,
        "name": domain.name,
        "description": domain.description,
        "topics": domain.topics,
        "scoring_dimensions": domain.scoring_dimensions,
        "question_count": len(domain.get_questions()),
        "skill_categories": list(domain.get_skills().keys()),
    }


@router.get("/{slug}/questions")
def get_domain_questions(slug: str, difficulty: str = None, topic: str = None):
    """Get questions for a domain, optionally filtered by difficulty or topic."""
    registry = get_registry()
    domain = registry.get(slug)
    if not domain:
        raise HTTPException(status_code=404, detail=f"Domain '{slug}' not found")

    questions = domain.get_questions()

    if difficulty:
        questions = [q for q in questions if q["difficulty"] == difficulty]
    if topic:
        questions = [q for q in questions if q["topic"] == topic]

    return {"domain": slug, "count": len(questions), "questions": questions}


@router.get("/{slug}/skills")
def get_domain_skills(slug: str):
    """Get skills organized by category for a domain."""
    registry = get_registry()
    domain = registry.get(slug)
    if not domain:
        raise HTTPException(status_code=404, detail=f"Domain '{slug}' not found")

    return {"domain": slug, "skills": domain.get_skills()}
