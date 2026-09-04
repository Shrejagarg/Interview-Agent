"""Credits DB helpers — lazy monthly reset, uncapped by default (credits_total=0 means unlimited)."""

import logging
from datetime import datetime
from typing import Optional
import uuid

from backend.app.db.database import SessionLocal
from backend.app.db.models import CreditAllotment

logger = logging.getLogger(__name__)

DEFAULT_MONTHLY_CREDITS = 0  # 0 = uncapped


def get_or_create_allotment(user_id: str) -> CreditAllotment:
    """Return the user's credit row, creating it with defaults if missing."""
    with SessionLocal() as db:
        allotment = db.query(CreditAllotment).filter(CreditAllotment.user_id == user_id).first()
        if not allotment:
            allotment = CreditAllotment(
                id=str(uuid.uuid4()),
                user_id=user_id,
                credits_total=DEFAULT_MONTHLY_CREDITS,
                credits_used=0,
                credit_last_reset_at=datetime.utcnow(),
            )
            db.add(allotment)
            db.commit()
            db.refresh(allotment)
        return allotment


def ensure_credits_ready(user_id: str) -> CreditAllotment:
    """Lazy reset: zero credits_used if we're in a new calendar month.

    Called on every credit check so we never need a scheduler.
    """
    with SessionLocal() as db:
        allotment = db.query(CreditAllotment).filter(CreditAllotment.user_id == user_id).first()
        if not allotment:
            allotment = CreditAllotment(
                id=str(uuid.uuid4()),
                user_id=user_id,
                credits_total=DEFAULT_MONTHLY_CREDITS,
                credits_used=0,
                credit_last_reset_at=datetime.utcnow(),
            )
            db.add(allotment)
            db.commit()
            db.refresh(allotment)
            return allotment

        now = datetime.utcnow()
        last_reset = allotment.credit_last_reset_at or now
        if now.year != last_reset.year or now.month != last_reset.month:
            logger.info("Monthly credit reset for user %s (was %d used).", user_id, allotment.credits_used)
            allotment.credits_used = 0
            allotment.credit_last_reset_at = now
            db.commit()
            db.refresh(allotment)

        return allotment


def has_credits(user_id: str) -> bool:
    """Return True if the user is allowed to start another interview.

    credits_total == 0 means uncapped — always returns True.
    """
    allotment = ensure_credits_ready(user_id)
    if allotment.credits_total == 0:
        return True  # uncapped
    return allotment.credits_used < allotment.credits_total


def deduct_credit(user_id: str) -> None:
    """Increment credits_used by 1. Idempotent when uncapped."""
    with SessionLocal() as db:
        allotment = db.query(CreditAllotment).filter(CreditAllotment.user_id == user_id).first()
        if allotment:
            allotment.credits_used = (allotment.credits_used or 0) + 1
            db.commit()


def get_credit_summary(user_id: str) -> dict:
    """Return credit status for the /api/me/credits endpoint."""
    allotment = ensure_credits_ready(user_id)
    now = datetime.utcnow()
    # Compute reset date: 1st of next month
    if now.month == 12:
        resets_at = datetime(now.year + 1, 1, 1)
    else:
        resets_at = datetime(now.year, now.month + 1, 1)

    uncapped = allotment.credits_total == 0
    return {
        "credits_total":     allotment.credits_total,
        "credits_used":      allotment.credits_used,
        "credits_remaining": None if uncapped else max(0, allotment.credits_total - allotment.credits_used),
        "uncapped":          uncapped,
        "resets_at":         resets_at.isoformat(),
    }
