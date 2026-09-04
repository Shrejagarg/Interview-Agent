"""Result share-link DB helpers.

A company can mint a token that exposes a read-only copy of a candidate's
interview report. Tokens expire (optional) and can be revoked by the owner.
"""

import uuid
from typing import Optional
from datetime import datetime, timedelta

from backend.app.db.database import SessionLocal
from backend.app.db.models import ResultShare

DEFAULT_TTL_DAYS = 30


def create_share_db(session_id: str, created_by: str, expires_in_days: int = DEFAULT_TTL_DAYS) -> dict:
    """Create a share token for a session. Returns the token + expiry."""
    token = uuid.uuid4().hex
    expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
    with SessionLocal() as db:
        share = ResultShare(
            token=token,
            session_id=session_id,
            created_by=created_by,
            expires_at=expires_at,
            created_at=datetime.utcnow(),
        )
        db.add(share)
        db.commit()
        db.refresh(share)
        return _share_to_dict(share)


def get_share_db(token: str) -> Optional[dict]:
    """Return a valid (unexpired) share, or None if missing/expired/revoked."""
    with SessionLocal() as db:
        share = db.query(ResultShare).filter(ResultShare.token == token).first()
        if not share:
            return None
        if share.revoked:
            return None
        if share.expires_at and share.expires_at < datetime.utcnow():
            return None
        return _share_to_dict(share)


def get_shares_for_session_db(session_id: str, created_by: Optional[str] = None) -> list[dict]:
    with SessionLocal() as db:
        q = db.query(ResultShare).filter(ResultShare.session_id == session_id)
        if created_by:
            q = q.filter(ResultShare.created_by == created_by)
        return [_share_to_dict(s) for s in q.all()]


def revoke_share_db(token: str, created_by: str) -> bool:
    """Mark a share as revoked (only the creating user may revoke)."""
    with SessionLocal() as db:
        share = db.query(ResultShare).filter(
            ResultShare.token == token,
            ResultShare.created_by == created_by,
        ).first()
        if not share:
            return False
        share.revoked = True
        db.commit()
        return True


def _share_to_dict(share: ResultShare) -> dict:
    return {
        "token": share.token,
        "session_id": share.session_id,
        "created_by": share.created_by,
        "expires_at": share.expires_at.isoformat() if share.expires_at else None,
        "created_at": share.created_at.isoformat() if share.created_at else None,
        "revoked": share.revoked,
        "share_url": f"/api/reports/shared/{share.token}",
    }
