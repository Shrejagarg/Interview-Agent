"""Invite CRUD helpers — powered by SQLAlchemy."""

import logging
from typing import Optional
from datetime import datetime

from backend.app.db.database import SessionLocal
from backend.app.db.models import Invite

logger = logging.getLogger(__name__)

def create_invite_db(invite_data: dict) -> None:
    """Create an invite record."""
    with SessionLocal() as db:
        invite = Invite(
            token=invite_data["token"],
            company_id=invite_data["company_id"],
            domain_slug=invite_data["domain_slug"],
            question_count=invite_data.get("question_count", 5),
            experience_level=invite_data.get("experience_level"),
            status=invite_data.get("status", "active")
        )
        db.add(invite)
        try:
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error("Failed to create invite %s: %s", invite_data["token"], e)
            raise


def get_invite_db(token: str) -> Optional[dict]:
    """Get an invite by token."""
    with SessionLocal() as db:
        invite = db.query(Invite).filter(Invite.token == token).first()
        if not invite:
            return None
        return {
            "token": invite.token,
            "company_id": invite.company_id,
            "domain_slug": invite.domain_slug,
            "question_count": invite.question_count,
            "experience_level": invite.experience_level,
            "status": invite.status,
            "created_at": invite.created_at.isoformat() if invite.created_at else None
        }


def mark_invite_used_db(token: str, session_id: str) -> None:
    """Mark an invite as used."""
    with SessionLocal() as db:
        invite = db.query(Invite).filter(Invite.token == token).first()
        if invite:
            invite.status = "used"
            # Note: We don't have used_by_session_id in the models right now to keep it simple,
            # but we update the status to prevent reuse
            try:
                db.commit()
            except Exception as e:
                db.rollback()
                logger.error("Failed to mark invite %s as used: %s", token, e)
                raise
