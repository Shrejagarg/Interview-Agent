"""Session CRUD helpers — all Supabase reads/writes for interview sessions.

Every function works with the raw ``state`` dictionary that
``core.engine.InterviewEngine`` produces.  The ``raw_state`` JSONB column
stores the complete dict; denormalised columns (``id``, ``domain``, …) are
kept in sync for fast queries and RLS policies.
"""

import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

from backend.app.config import is_supabase_configured, ENV
from backend.app.db.supabase import get_db_or_raise

logger = logging.getLogger(__name__)

TABLE = "sessions"

# ── Dev-mode in-memory fallback ───────────────────────────────────────────────
_dev_sessions: Dict[str, dict] = {}


def _state_to_row(state: dict) -> dict:
    """Extract denormalised columns from a state dict for the sessions table."""
    return {
        "id": state["session_id"],
        "user_id": state.get("user_id"),
        "company_id": state.get("company_id"),
        "domain_slug": state["domain"],
        "status": state.get("status", "not_started"),
        "average_score": state.get("_avg", 0),
        "verdict": state.get("verdict"),
        "started_at": state.get("started_at"),
        "finished_at": state.get("finished_at"),
        "question_count": state.get("total_questions", 0),
        "raw_state": state,
    }


def _row_to_state(row: dict) -> dict:
    """Extract the raw_state dict from a database row."""
    if row is None:
        return None
    raw = row.get("raw_state")
    if isinstance(raw, str):
        import json
        raw = json.loads(raw)
    return raw


# ── Write ─────────────────────────────────────────────────────────────────────

def save_session_db(state: dict) -> None:
    """Upsert a session state into Supabase (or in-memory if not configured)."""
    if not is_supabase_configured():
        if ENV == "development":
            _dev_sessions[state["session_id"]] = _state_to_row(state)
            return
        raise RuntimeError("Supabase is not configured.")

    db = get_db_or_raise()
    row = _state_to_row(state)
    try:
        db.table(TABLE).upsert(row, on_conflict="id").execute()
    except Exception as e:
        logger.error("Failed to save session %s: %s", state.get("session_id"), e)
        raise


# ── Read ──────────────────────────────────────────────────────────────────────

def load_session_db(session_id: str) -> Optional[dict]:
    """Load a single session state by ID. Returns None if not found."""
    if not is_supabase_configured():
        if ENV == "development":
            row = _dev_sessions.get(session_id)
            return _row_to_state(row)
        raise RuntimeError("Supabase is not configured.")

    db = get_db_or_raise()
    try:
        resp = db.table(TABLE).select("raw_state").eq("id", session_id).limit(1).execute()
        rows = resp.data
        if not rows:
            return None
        return _row_to_state(rows[0])
    except Exception as e:
        logger.error("Failed to load session %s: %s", session_id, e)
        raise


def get_company_sessions_db(company_id: str) -> List[dict]:
    """Return all session states linked to a company."""
    if not is_supabase_configured():
        if ENV == "development":
            rows = [r for r in _dev_sessions.values() if r.get("company_id") == company_id]
            # sort by started_at desc
            rows.sort(key=lambda x: x.get("started_at") or "", reverse=True)
            return [_row_to_state(r) for r in rows if _row_to_state(r) is not None]
        raise RuntimeError("Supabase is not configured.")

    db = get_db_or_raise()
    try:
        resp = (
            db.table(TABLE)
            .select("raw_state")
            .eq("company_id", company_id)
            .order("started_at", desc=True)
            .execute()
        )
        return [_row_to_state(r) for r in resp.data if _row_to_state(r) is not None]
    except Exception as e:
        logger.error("Failed to load sessions for company %s: %s", company_id, e)
        raise


def get_user_sessions_db(user_id: str) -> List[dict]:
    """Return all session states for a user."""
    if not is_supabase_configured():
        if ENV == "development":
            rows = [r for r in _dev_sessions.values() if r.get("user_id") == user_id]
            rows.sort(key=lambda x: x.get("started_at") or "", reverse=True)
            return [_row_to_state(r) for r in rows if _row_to_state(r) is not None]
        raise RuntimeError("Supabase is not configured.")

    db = get_db_or_raise()
    try:
        resp = (
            db.table(TABLE)
            .select("raw_state")
            .eq("user_id", user_id)
            .order("started_at", desc=True)
            .execute()
        )
        return [_row_to_state(r) for r in resp.data if _row_to_state(r) is not None]
    except Exception as e:
        logger.error("Failed to load sessions for user %s: %s", user_id, e)
        raise


def get_all_sessions_db() -> List[dict]:
    """Return all session states (analytics / admin)."""
    if not is_supabase_configured():
        if ENV == "development":
            rows = list(_dev_sessions.values())
            rows.sort(key=lambda x: x.get("started_at") or "", reverse=True)
            return [_row_to_state(r) for r in rows if _row_to_state(r) is not None]
        raise RuntimeError("Supabase is not configured.")

    db = get_db_or_raise()
    try:
        resp = (
            db.table(TABLE)
            .select("raw_state")
            .order("started_at", desc=True)
            .execute()
        )
        return [_row_to_state(r) for r in resp.data if _row_to_state(r) is not None]
    except Exception as e:
        logger.error("Failed to load all sessions: %s", e)
        raise


def get_sessions_by_domain_db(domain_slug: str) -> List[dict]:
    """Return all session states for a specific domain."""
    if not is_supabase_configured():
        if ENV == "development":
            rows = [r for r in _dev_sessions.values() if r.get("domain_slug") == domain_slug]
            rows.sort(key=lambda x: x.get("started_at") or "", reverse=True)
            return [_row_to_state(r) for r in rows if _row_to_state(r) is not None]
        raise RuntimeError("Supabase is not configured.")

    db = get_db_or_raise()
    try:
        resp = (
            db.table(TABLE)
            .select("raw_state")
            .eq("domain_slug", domain_slug)
            .order("started_at", desc=True)
            .execute()
        )
        return [_row_to_state(r) for r in resp.data if _row_to_state(r) is not None]
    except Exception as e:
        logger.error("Failed to load sessions for domain %s: %s", domain_slug, e)
        raise
