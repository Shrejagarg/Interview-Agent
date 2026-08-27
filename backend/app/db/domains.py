"""Domain database helpers — SQLAlchemy version.

These functions mirror the old Supabase domain CRUD but use the
existing ``domains``, ``questions``, ``skills``, and ``job_titles``
tables created by ``supabase/schema.sql``.
"""

import json
import logging
from typing import Optional
from sqlalchemy import text
from backend.app.db.database import SessionLocal

logger = logging.getLogger(__name__)


def list_domains_db() -> list[dict]:
    """Return all active domains as a list of dicts."""
    db = SessionLocal()
    try:
        rows = db.execute(text("SELECT id, slug, name, description, topics, scoring_dimensions, is_active FROM domains WHERE is_active = :active"), {"active": True}).fetchall()
        return [
            {
                "id": str(r.id),
                "slug": r.slug,
                "name": r.name,
                "description": r.description or "",
                "topics": json.loads(r.topics) if isinstance(r.topics, str) else (r.topics or []),
                "scoring_dimensions": json.loads(r.scoring_dimensions) if isinstance(r.scoring_dimensions, str) else (r.scoring_dimensions or []),
                "is_active": r.is_active,
            }
            for r in rows
        ]
    except Exception as e:
        logger.warning("list_domains_db failed: %s", e)
        return []
    finally:
        db.close()


def get_domain_db(slug: str) -> Optional[dict]:
    """Return a single domain dict by slug, or None."""
    db = SessionLocal()
    try:
        r = db.execute(text("SELECT id, slug, name, description, topics, scoring_dimensions, is_active FROM domains WHERE slug = :slug"), {"slug": slug}).fetchone()
        if not r:
            return None
        return {
            "id": str(r.id),
            "slug": r.slug,
            "name": r.name,
            "description": r.description or "",
            "topics": json.loads(r.topics) if isinstance(r.topics, str) else (r.topics or []),
            "scoring_dimensions": json.loads(r.scoring_dimensions) if isinstance(r.scoring_dimensions, str) else (r.scoring_dimensions or []),
            "is_active": r.is_active,
        }
    except Exception as e:
        logger.warning("get_domain_db failed for %s: %s", slug, e)
        return None
    finally:
        db.close()


def get_domain_questions_db(domain_id: str) -> list[dict]:
    """Return all active questions for a domain."""
    db = SessionLocal()
    try:
        rows = db.execute(
            text("SELECT id, domain_id, domain_slug, external_id, topic, difficulty, roles, question_text, is_active FROM questions WHERE domain_id = :did AND is_active = :active"),
            {"did": domain_id, "active": True},
        ).fetchall()
        return [
            {
                "id": str(r.id),
                "domain_id": str(r.domain_id),
                "domain_slug": r.domain_slug,
                "external_id": r.external_id,
                "topic": r.topic,
                "difficulty": r.difficulty,
                "roles": json.loads(r.roles) if isinstance(r.roles, str) else (r.roles or []),
                "question_text": r.question_text,
                "is_active": r.is_active,
            }
            for r in rows
        ]
    except Exception as e:
        logger.warning("get_domain_questions_db failed for %s: %s", domain_id, e)
        return []
    finally:
        db.close()


def get_domain_skills_db(domain_id: str) -> list[dict]:
    """Return all skills for a domain."""
    db = SessionLocal()
    try:
        rows = db.execute(
            text("SELECT id, domain_id, domain_slug, category, skill_name FROM skills WHERE domain_id = :did"),
            {"did": domain_id},
        ).fetchall()
        return [
            {
                "id": str(r.id),
                "domain_id": str(r.domain_id),
                "domain_slug": r.domain_slug,
                "category": r.category,
                "skill_name": r.skill_name,
            }
            for r in rows
        ]
    except Exception as e:
        logger.warning("get_domain_skills_db failed for %s: %s", domain_id, e)
        return []
    finally:
        db.close()


def get_domain_job_titles_db(domain_id: str) -> list[dict]:
    """Return all job titles for a domain."""
    db = SessionLocal()
    try:
        rows = db.execute(
            text("SELECT id, domain_id, level, title FROM job_titles WHERE domain_id = :did"),
            {"did": domain_id},
        ).fetchall()
        return [
            {
                "id": str(r.id),
                "domain_id": str(r.domain_id),
                "level": r.level,
                "title": r.title,
            }
            for r in rows
        ]
    except Exception as e:
        logger.warning("get_domain_job_titles_db failed for %s: %s", domain_id, e)
        return []
    finally:
        db.close()
