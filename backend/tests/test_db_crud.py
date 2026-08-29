"""Unit tests for the SQLAlchemy session/invite CRUD helpers.

These run against the throwaway temp DB (the DATABASE_URL override in conftest)
rather than the mock dict store, so the real db/sessions.py and db/invites.py
code paths are exercised. The dev database is untouched.
"""

import pytest

from backend.app.db.database import SessionLocal
from backend.app.db.sessions import (
    save_session_db,
    load_session_db,
    get_company_sessions_db,
    get_user_sessions_db,
    get_all_sessions_db,
    get_sessions_by_domain_db,
)
from backend.app.db.invites import create_invite_db, get_invite_db, mark_invite_used_db


def _state(sid: str, status: str = "in_progress", **overrides) -> dict:
    state = {
        "session_id": sid,
        "user_id": "u1",
        "company_id": None,
        "domain": "marketing",
        "status": status,
        "started_at": "2026-01-01T10:00:00",
        "finished_at": None,
        "answers": [],
        "question_index": 0,
        "total_questions": 5,
        "current_question": {"id": "q1", "question": "What is marketing?"},
    }
    state.update(overrides)
    return state


# ── Session CRUD ──────────────────────────────────────────────────────────────

class TestSessionCrud:
    def test_save_and_load_roundtrip(self):
        state = _state("s1")
        save_session_db(state)
        assert load_session_db("s1") == state

    def test_upsert_updates_existing_row(self):
        save_session_db(_state("s1"))
        save_session_db(_state("s1", status="completed", finished_at="2026-01-01T11:00:00"))
        loaded = load_session_db("s1")
        assert loaded["status"] == "completed"
        assert loaded["finished_at"] == "2026-01-01T11:00:00"

    def test_load_missing_returns_none(self):
        assert load_session_db("does-not-exist") is None

    def test_invalid_started_at_falls_back_to_now(self):
        save_session_db(_state("s2", started_at="not-a-date"))
        loaded = load_session_db("s2")
        assert loaded["started_at"] is not None

    def test_get_company_sessions(self):
        save_session_db(_state("c1", company_id="comp-a"))
        save_session_db(_state("c2", company_id="comp-a"))
        save_session_db(_state("c3", company_id="comp-b"))
        ids = {s["session_id"] for s in get_company_sessions_db("comp-a")}
        assert ids == {"c1", "c2"}

    def test_get_user_sessions(self):
        save_session_db(_state("u1"))
        save_session_db(_state("u2"))
        ids = {s["session_id"] for s in get_user_sessions_db("u1")}
        assert ids == {"u1", "u2"}
        assert get_user_sessions_db("other") == []

    def test_get_all_sessions_ordered(self):
        save_session_db(_state("early", started_at="2026-01-01T10:00:00"))
        save_session_db(_state("late", started_at="2026-01-02T10:00:00"))
        result = get_all_sessions_db()
        assert result[0]["session_id"] == "late"

    def test_get_sessions_by_domain(self):
        save_session_db(_state("m1", domain="marketing"))
        save_session_db(_state("hr1", domain="hr"))
        result = get_sessions_by_domain_db("hr")
        assert [s["session_id"] for s in result] == ["hr1"]

    def test_save_rollback_on_failure(self):
        # Missing "domain" key -> INSERT fails -> rollback path runs, no crash
        from backend.app.db.sessions import save_session_db as save
        with pytest.raises(Exception):
            save({"session_id": "broken"})
        assert load_session_db("broken") is None


# ── Invite CRUD ───────────────────────────────────────────────────────────────

class TestInviteCrud:
    def test_create_and_get_roundtrip(self):
        create_invite_db({
            "token": "tok1",
            "company_id": "comp-a",
            "domain_slug": "marketing",
        })
        invite = get_invite_db("tok1")
        assert invite["company_id"] == "comp-a"
        assert invite["domain_slug"] == "marketing"
        assert invite["question_count"] == 5
        assert invite["status"] == "active"
        assert invite["created_at"] is not None

    def test_create_with_optional_fields(self):
        create_invite_db({
            "token": "tok2",
            "company_id": "comp-b",
            "domain_slug": "finance",
            "question_count": 3,
            "experience_level": "senior",
            "status": "pending",
        })
        invite = get_invite_db("tok2")
        assert invite["question_count"] == 3
        assert invite["experience_level"] == "senior"
        assert invite["status"] == "pending"

    def test_get_missing_returns_none(self):
        assert get_invite_db("missing") is None

    def test_mark_used(self):
        create_invite_db({"token": "tok3", "company_id": "comp-a", "domain_slug": "marketing"})
        mark_invite_used_db("tok3", "session-xyz")
        assert get_invite_db("tok3")["status"] == "used"

    def test_mark_used_unknown_token_is_noop(self):
        mark_invite_used_db("nope", "session-xyz")  # should not raise