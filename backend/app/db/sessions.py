"""Session CRUD helpers — powered by SQLAlchemy."""

import logging
from datetime import datetime
from typing import Dict, List, Optional
import json

from backend.app.db.database import SessionLocal
from backend.app.db.models import InterviewSession

logger = logging.getLogger(__name__)

def save_session_db(state: dict) -> None:
    """Upsert a session state into the database."""
    session_id = state["session_id"]
    
    with SessionLocal() as db:
        session = db.query(InterviewSession).filter(InterviewSession.id == session_id).first()
        
        # Helper to parse dates
        started_at = state.get("started_at")
        if isinstance(started_at, str):
            try:
                started_at = datetime.fromisoformat(started_at)
            except ValueError:
                started_at = datetime.utcnow()
        if not started_at:
            started_at = datetime.utcnow()
            
        finished_at = state.get("finished_at")
        if isinstance(finished_at, str):
            try:
                finished_at = datetime.fromisoformat(finished_at)
            except ValueError:
                finished_at = None

        if not session:
            session = InterviewSession(
                id=session_id,
                user_id=state.get("user_id"),
                company_id=state.get("company_id"),
                domain_slug=state["domain"],
                status=state.get("status", "not_started"),
                started_at=started_at,
                finished_at=finished_at,
                state_data=state
            )
            db.add(session)
        else:
            session.user_id = state.get("user_id")
            session.company_id = state.get("company_id")
            session.domain_slug = state["domain"]
            session.status = state.get("status", "not_started")
            session.started_at = started_at
            session.finished_at = finished_at
            # Make sure we trigger SQLAlchemy JSON mutation detection by assigning a new dict or using flag_modified
            session.state_data = dict(state)

        try:
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error("Failed to save session %s: %s", session_id, e)
            raise


def load_session_db(session_id: str) -> Optional[dict]:
    """Load a single session state by ID."""
    with SessionLocal() as db:
        session = db.query(InterviewSession).filter(InterviewSession.id == session_id).first()
        if not session:
            return None
        return session.state_data


def get_company_sessions_db(company_id: str) -> List[dict]:
    """Return all session states linked to a company."""
    with SessionLocal() as db:
        sessions = db.query(InterviewSession).filter(InterviewSession.company_id == company_id).order_by(InterviewSession.started_at.desc()).all()
        return [s.state_data for s in sessions]


def get_user_sessions_db(user_id: str) -> List[dict]:
    """Return all session states for a user."""
    with SessionLocal() as db:
        sessions = db.query(InterviewSession).filter(InterviewSession.user_id == user_id).order_by(InterviewSession.started_at.desc()).all()
        return [s.state_data for s in sessions]


def get_all_sessions_db() -> List[dict]:
    """Return all session states (analytics / admin)."""
    with SessionLocal() as db:
        sessions = db.query(InterviewSession).order_by(InterviewSession.started_at.desc()).all()
        return [s.state_data for s in sessions]


def get_sessions_by_domain_db(domain_slug: str) -> List[dict]:
    """Return all session states for a specific domain."""
    with SessionLocal() as db:
        sessions = db.query(InterviewSession).filter(InterviewSession.domain_slug == domain_slug).order_by(InterviewSession.started_at.desc()).all()
        return [s.state_data for s in sessions]
