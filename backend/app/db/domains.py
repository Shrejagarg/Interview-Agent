from backend.app.db.supabase import get_db_or_raise
import logging

logger = logging.getLogger(__name__)


def get_domain_db(slug: str) -> dict:
    """Fetch domain metadata from the 'domains' table."""
    db = get_db_or_raise()
    resp = db.table("domains").select("*").eq("slug", slug).execute()
    return resp.data[0] if resp.data else None


def list_domains_db() -> list[dict]:
    """Fetch all domains from the 'domains' table."""
    db = get_db_or_raise()
    resp = db.table("domains").select("*").execute()
    return resp.data


def get_domain_questions_db(domain_id: str) -> list[dict]:
    """Fetch all questions for a specific domain from the 'questions' table."""
    db = get_db_or_raise()
    resp = (
        db.table("questions")
        .select("*")
        .eq("domain_id", domain_id)
        .eq("is_active", True)
        .execute()
    )
    return resp.data


def get_domain_skills_db(domain_id: str) -> list[dict]:
    """Fetch all skills for a specific domain from the 'skills' table."""
    db = get_db_or_raise()
    resp = (
        db.table("skills")
        .select("*")
        .eq("domain_id", domain_id)
        .execute()
    )
    return resp.data


def get_domain_job_titles_db(domain_id: str) -> list[dict]:
    """Fetch all job titles for a specific domain from the 'job_titles' table."""
    db = get_db_or_raise()
    resp = (
        db.table("job_titles")
        .select("*")
        .eq("domain_id", domain_id)
        .execute()
    )
    return resp.data
