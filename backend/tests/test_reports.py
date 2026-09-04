"""Endpoint tests for ARC IV report export (shareable report links).

Runs against the throwaway temp DB bound by conftest, with the in-memory mocked
session store patched in, so the dev database is never touched.
"""

import uuid
from datetime import datetime

from fastapi.testclient import TestClient

from backend.app import app
from backend.app.api.auth import _make_token
from backend.app.db import database
from backend.app.db.models import User
from backend.tests import conftest  # noqa: F401  (temp-DB quarantine)
from backend.tests.conftest import _mock_sessions

client = TestClient(app)


def _seed_user(role: str):
    user_id = str(uuid.uuid4())
    email = f"{role}_{uuid.uuid4().hex[:8]}@test.com"
    with database.SessionLocal() as db:
        db.add(User(id=user_id, email=email, password_hash="x", role=role, full_name=role))
        db.commit()
    return user_id, _make_token(user_id, role)


def _seed_session(session_id: str, company_id: str):
    _mock_sessions[session_id] = {
        "session_id": session_id,
        "user_id": "candidate-1",
        "company_id": company_id,
        "domain": "marketing",
        "status": "completed",
        "started_at": "2026-09-01T10:00:00",
        "finished_at": "2026-09-01T10:30:00",
        "total_questions": 1,
        "answers": [],
        "_avg": 8.5,
        "role_context": {"experience_level": "mid"},
        "topic_scores": {"digital_marketing": 8.0},
        "verdict": "Hire",
        "seriousness_flags": [],
    }


def _fresh_shares():
    from sqlalchemy import text
    with database.engine.begin() as conn:
        conn.execute(text("DELETE FROM result_shares"))


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


class TestCreateShare:
    def test_company_creates_share_for_own_session(self):
        _fresh_shares()
        cid, token = _seed_user("company")
        session_id = "sess-" + uuid.uuid4().hex[:8]
        _seed_session(session_id, cid)
        r = client.post(f"/api/reports/{session_id}/share", json={"expires_in_days": 30},
                        headers=_auth(token))
        assert r.status_code == 201, r.text
        data = r.json()
        assert data["share_url"] == f"/api/reports/shared/{data['token']}"
        for _ in range(3):
            _mock_sessions.pop(session_id, None)

    def test_cannot_share_another_companys_session(self):
        _fresh_shares()
        cid, token = _seed_user("company")
        other, _ = _seed_user("company")
        session_id = "sess-other-" + uuid.uuid4().hex[:6]
        _seed_session(session_id, other)
        r = client.post(f"/api/reports/{session_id}/share", json={}, headers=_auth(token))
        assert r.status_code == 404
        _mock_sessions.pop(session_id, None)

    def test_candidate_cannot_share(self):
        _fresh_shares()
        _, token = _seed_user("candidate")
        r = client.post("/api/reports/nope/share", json={}, headers=_auth(token))
        assert r.status_code == 403


class TestSharedReport:
    def test_public_get_shared_report(self):
        _fresh_shares()
        cid, token = _seed_user("company")
        session_id = "sess-pub-" + uuid.uuid4().hex[:6]
        _seed_session(session_id, cid)
        share = client.post(f"/api/reports/{session_id}/share", json={}, headers=_auth(token)).json()
        r = client.get(share["share_url"])
        assert r.status_code == 200
        data = r.json()
        assert data["report"]["session_id"] == session_id
        assert data["report"]["overall_score"] == 8.5
        _mock_sessions.pop(session_id, None)

    def test_unknown_token_404(self):
        r = client.get("/api/reports/shared/bogus-token")
        assert r.status_code == 404

    def test_requires_token(self):
        r = client.get("/api/reports/shared/")
        assert r.status_code != 200


class TestRevokeAndList:
    def test_revoke_then_public_404(self):
        _fresh_shares()
        cid, token = _seed_user("company")
        session_id = "sess-revoke-" + uuid.uuid4().hex[:6]
        _seed_session(session_id, cid)
        token_str = client.post(f"/api/reports/{session_id}/share", json={}, headers=_auth(token)).json()["token"]
        url = f"/api/reports/shared/{token_str}"
        assert client.get(url).status_code == 200

        r = client.delete(f"/api/reports/share/{token_str}", headers=_auth(token))
        assert r.status_code == 200
        assert r.json()["revoked"] is True
        assert client.get(url).status_code == 404
        _mock_sessions.pop(session_id, None)

    def test_revoke_by_nonowner_404(self):
        _fresh_shares()
        cid, token = _seed_user("company")
        other, other_token = _seed_user("company")
        session_id = "sess-ro-" + uuid.uuid4().hex[:6]
        _seed_session(session_id, cid)
        token_str = client.post(f"/api/reports/{session_id}/share", json={}, headers=_auth(token)).json()["token"]
        assert client.delete(f"/api/reports/share/{token_str}", headers=_auth(other_token)).status_code == 404
        _mock_sessions.pop(session_id, None)

    def test_list_shares(self):
        _fresh_shares()
        cid, token = _seed_user("company")
        session_id = "sess-list-" + uuid.uuid4().hex[:6]
        _seed_session(session_id, cid)
        client.post(f"/api/reports/{session_id}/share", json={}, headers=_auth(token))
        r = client.get(f"/api/reports/session/{session_id}/shares", headers=_auth(token))
        assert r.status_code == 200
        assert len(r.json()["shares"]) == 1
        _mock_sessions.pop(session_id, None)
