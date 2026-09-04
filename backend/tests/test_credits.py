"""Unit tests for the ARC IV credit DB helpers (lazy monthly reset, uncapped default).

Runs against the throwaway temp DB bound by conftest's DATABASE_URL override, so
the dev database is never touched. The temp tables are reset before each test.
"""

import uuid
from datetime import datetime

from backend.app.db import credits as credits_db
from backend.app.db import database
from backend.app.db.models import CreditAllotment
from backend.tests import conftest  # noqa: F401  (temp-DB quarantine)


def _fresh_db():
    engine = database.engine
    from sqlalchemy import text
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM credit_allotments"))


def _set_allotment(uid, total=None, used=None, last_reset=None):
    """Mutate an existing allotment row through a live session (detached-obj-safe)."""
    with database.SessionLocal() as db:
        row = db.query(CreditAllotment).filter(CreditAllotment.user_id == uid).first()
        if total is not None:
            row.credits_total = total
        if used is not None:
            row.credits_used = used
        if last_reset is not None:
            row.credit_last_reset_at = last_reset
        db.commit()


class TestGetOrCreateAllotment:
    def test_creates_row_with_defaults(self):
        _fresh_db()
        uid = "user-" + str(uuid.uuid4())
        a = credits_db.get_or_create_allotment(uid)
        assert a.user_id == uid
        assert a.credits_total == 0
        assert a.credits_used == 0

    def test_returns_existing_row(self):
        _fresh_db()
        uid = "user-" + str(uuid.uuid4())
        first = credits_db.get_or_create_allotment(uid)
        second = credits_db.get_or_create_allotment(uid)
        assert first.id == second.id

    def test_persists_row(self):
        _fresh_db()
        uid = "user-" + str(uuid.uuid4())
        credits_db.get_or_create_allotment(uid)
        with database.SessionLocal() as db:
            row = db.query(CreditAllotment).filter(CreditAllotment.user_id == uid).first()
            assert row is not None


class TestEnsureCreditsReady:
    def test_uncapped_does_not_reset_used(self):
        _fresh_db()
        uid = "user-" + str(uuid.uuid4())
        credits_db.get_or_create_allotment(uid)
        credits_db.deduct_credit(uid)
        a = credits_db.ensure_credits_ready(uid)
        assert a.credits_used == 1
        assert a.credits_total == 0  # uncapped

    def test_resets_used_in_new_month(self):
        _fresh_db()
        uid = "user-" + str(uuid.uuid4())
        credits_db.get_or_create_allotment(uid)
        _set_allotment(uid, used=10, last_reset=datetime(2000, 1, 1))  # old month
        refreshed = credits_db.ensure_credits_ready(uid)
        assert refreshed.credits_used == 0
        assert refreshed.credit_last_reset_at.year != 2000


class TestHasCredits:
    def test_uncapped_always_true(self):
        _fresh_db()
        uid = "user-" + str(uuid.uuid4())
        credits_db.get_or_create_allotment(uid)
        for _ in range(3):
            credits_db.deduct_credit(uid)
        assert credits_db.has_credits(uid) is True

    def test_capped_true_when_under_limit(self):
        _fresh_db()
        uid = "user-" + str(uuid.uuid4())
        credits_db.get_or_create_allotment(uid)
        _set_allotment(uid, total=5, used=3)
        assert credits_db.has_credits(uid) is True

    def test_capped_false_when_limit_reached(self):
        _fresh_db()
        uid = "user-" + str(uuid.uuid4())
        credits_db.get_or_create_allotment(uid)
        _set_allotment(uid, total=2, used=2)
        assert credits_db.has_credits(uid) is False


class TestDeductCredit:
    def test_increments_used(self):
        _fresh_db()
        uid = "user-" + str(uuid.uuid4())
        credits_db.get_or_create_allotment(uid)
        credits_db.deduct_credit(uid)
        a = credits_db.get_or_create_allotment(uid)
        assert a.credits_used == 1

    def test_noop_when_no_row(self):
        _fresh_db()
        credits_db.deduct_credit("nobody")  # should not raise


class TestGetCreditSummary:
    def test_uncapped_summary(self):
        _fresh_db()
        uid = "user-" + str(uuid.uuid4())
        credits_db.get_or_create_allotment(uid)
        s = credits_db.get_credit_summary(uid)
        assert s["credits_total"] == 0
        assert s["uncapped"] is True
        assert s["credits_remaining"] is None
        assert s["resets_at"]

    def test_capped_summary_remaining(self):
        _fresh_db()
        uid = "user-" + str(uuid.uuid4())
        credits_db.get_or_create_allotment(uid)
        _set_allotment(uid, total=10, used=4)
        s = credits_db.get_credit_summary(uid)
        assert s["uncapped"] is False
        assert s["credits_remaining"] == 6
