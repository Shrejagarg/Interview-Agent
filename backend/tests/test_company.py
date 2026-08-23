"""Tests for company endpoints — dashboard, sessions, candidates, compare, invite"""

import sys
import os
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from fastapi.testclient import TestClient
from backend.app import app
from backend.app.api.interviews import _sessions
from backend.app.api.auth import UserProfile

AUTH_PATCH_TARGET = "backend.app.api.auth.get_current_user"


def _mock_llm(messages, *args, **kwargs):
    import json
    return {
        "message": {
            "content": json.dumps({
                "relevance": 7.5,
                "clarity": 8.0,
                "creativity": 6.5,
                "communication": 7.5,
                "overall_score": 7.5,
                "strengths": ["Good structure"],
                "weaknesses": ["Could be more specific"],
                "follow_up": "",
                "is_serious": True,
            })
        }
    }


COMPANY_USER = UserProfile(
    user_id="company-001",
    email="acme@corp.com",
    role="company",
    full_name="ACME Corp",
)

CANDIDATE_USER = UserProfile(
    user_id="cand-001",
    email="jane@example.com",
    role="candidate",
)


def _mock_company_auth(*args, **kwargs):
    return COMPANY_USER


def _mock_candidate_auth(*args, **kwargs):
    return CANDIDATE_USER


client = TestClient(app)

_patches = [
    patch("core.evaluator._call_llm", side_effect=_mock_llm),
    patch("core.engine.pre_screen_answer", return_value={"pass": True, "auto_score": 0}),
]


def setup_module():
    for p in _patches:
        p.start()
    _sessions.clear()


def teardown_module():
    for p in _patches:
        p.stop()
    _sessions.clear()


def _create_session_with_answers(
    domain: str,
    count: int = 2,
    user_id: str = "cand-001",
    company_id: str = "company-001",
) -> str:
    """Helper: create a session, link it to company, answer all questions."""
    resp = client.post("/api/interviews/start", json={
        "domain_slug": domain,
        "question_count": count,
    }, headers={"Authorization": "Bearer test-token"})
    sid = resp.json()["session_id"]

    session = _sessions[sid]
    session["user_id"] = user_id
    session["company_id"] = company_id

    while True:
        q = client.get(f"/api/interviews/{sid}/question")
        if q.status_code != 200:
            break
        body = q.json()
        client.post(f"/api/interviews/{sid}/answer", json={
            "question_id": body["id"],
            "answer_text": "Detailed answer covering the key points of the topic.",
        })

    return sid


# ── Dashboard ─────────────────────────────────────────────────────────────────

class TestCompanyDashboard:
    @patch(AUTH_PATCH_TARGET, side_effect=_mock_company_auth)
    def test_dashboard_returns_stats(self, _mock):
        _sessions.clear()
        _create_session_with_answers("marketing", count=2)
        _create_session_with_answers("finance", count=1)

        r = client.get("/api/company/dashboard", headers={"Authorization": "Bearer tok"})
        assert r.status_code == 200
        body = r.json()
        assert body["total_sessions"] == 2
        assert body["unique_candidates"] >= 1
        assert body["avg_score"] > 0
        assert "marketing" in body["domain_breakdown"]
        assert "finance" in body["domain_breakdown"]

    @patch(AUTH_PATCH_TARGET, side_effect=_mock_company_auth)
    def test_dashboard_empty(self, _mock):
        _sessions.clear()
        r = client.get("/api/company/dashboard", headers={"Authorization": "Bearer tok"})
        assert r.status_code == 200
        body = r.json()
        assert body["total_sessions"] == 0
        assert body["unique_candidates"] == 0
        assert body["avg_score"] == 0.0


# ── Role Enforcement ──────────────────────────────────────────────────────────

class TestRoleEnforcement:
    @patch(AUTH_PATCH_TARGET, side_effect=_mock_candidate_auth)
    def test_candidate_cannot_access_dashboard(self, _mock):
        r = client.get("/api/company/dashboard", headers={"Authorization": "Bearer tok"})
        assert r.status_code == 403

    @patch(AUTH_PATCH_TARGET, side_effect=_mock_candidate_auth)
    def test_candidate_cannot_access_sessions(self, _mock):
        r = client.get("/api/company/sessions", headers={"Authorization": "Bearer tok"})
        assert r.status_code == 403

    @patch(AUTH_PATCH_TARGET, side_effect=_mock_candidate_auth)
    def test_candidate_cannot_access_candidates(self, _mock):
        r = client.get("/api/company/candidates", headers={"Authorization": "Bearer tok"})
        assert r.status_code == 403

    @patch(AUTH_PATCH_TARGET, side_effect=_mock_candidate_auth)
    def test_candidate_cannot_invite(self, _mock):
        r = client.post("/api/company/invite", json={
            "email": "test@example.com",
            "domain_slug": "marketing",
        }, headers={"Authorization": "Bearer tok"})
        assert r.status_code == 403

    @patch(AUTH_PATCH_TARGET, side_effect=_mock_candidate_auth)
    def test_candidate_cannot_compare(self, _mock):
        r = client.get("/api/company/compare?session_ids=a,b", headers={"Authorization": "Bearer tok"})
        assert r.status_code == 403


# ── Sessions ──────────────────────────────────────────────────────────────────

class TestCompanySessions:
    @patch(AUTH_PATCH_TARGET, side_effect=_mock_company_auth)
    def test_list_sessions(self, _mock):
        _sessions.clear()
        _create_session_with_answers("marketing", count=2)
        _create_session_with_answers("finance", count=1)

        r = client.get("/api/company/sessions", headers={"Authorization": "Bearer tok"})
        assert r.status_code == 200
        assert len(r.json()["sessions"]) == 2

    @patch(AUTH_PATCH_TARGET, side_effect=_mock_company_auth)
    def test_list_sessions_filter_domain(self, _mock):
        _sessions.clear()
        _create_session_with_answers("marketing", count=1)
        _create_session_with_answers("finance", count=1)

        r = client.get("/api/company/sessions?domain=marketing", headers={"Authorization": "Bearer tok"})
        assert r.status_code == 200
        for s in r.json()["sessions"]:
            assert s["domain"] == "marketing"

    @patch(AUTH_PATCH_TARGET, side_effect=_mock_company_auth)
    def test_list_sessions_filter_status(self, _mock):
        _sessions.clear()
        _create_session_with_answers("marketing", count=1)

        r = client.get("/api/company/sessions?status=completed", headers={"Authorization": "Bearer tok"})
        assert r.status_code == 200
        for s in r.json()["sessions"]:
            assert s["status"] == "completed"

    @patch(AUTH_PATCH_TARGET, side_effect=_mock_company_auth)
    def test_get_session_detail(self, _mock):
        _sessions.clear()
        sid = _create_session_with_answers("marketing", count=1)

        r = client.get(f"/api/company/sessions/{sid}", headers={"Authorization": "Bearer tok"})
        assert r.status_code == 200
        body = r.json()
        assert body["session_id"] == sid
        assert body["status"] == "completed"
        assert body["overall_score"] > 0
        assert len(body["answers"]) == 1
        assert "topic_scores" in body
        assert "verdict" in body

    @patch(AUTH_PATCH_TARGET, side_effect=_mock_company_auth)
    def test_get_session_not_found(self, _mock):
        r = client.get("/api/company/sessions/fake-id", headers={"Authorization": "Bearer tok"})
        assert r.status_code == 404


# ── Candidates ────────────────────────────────────────────────────────────────

class TestCompanyCandidates:
    @patch(AUTH_PATCH_TARGET, side_effect=_mock_company_auth)
    def test_list_candidates(self, _mock):
        _sessions.clear()
        _create_session_with_answers("marketing", count=2, user_id="cand-001")
        _create_session_with_answers("finance", count=1, user_id="cand-002")

        r = client.get("/api/company/candidates", headers={"Authorization": "Bearer tok"})
        assert r.status_code == 200
        candidates = r.json()["candidates"]
        assert len(candidates) == 2

    @patch(AUTH_PATCH_TARGET, side_effect=_mock_company_auth)
    def test_candidates_have_scores(self, _mock):
        _sessions.clear()
        _create_session_with_answers("marketing", count=1, user_id="cand-001")

        r = client.get("/api/company/candidates", headers={"Authorization": "Bearer tok"})
        c = r.json()["candidates"][0]
        assert c["user_id"] == "cand-001"
        assert c["total_sessions"] == 1
        assert "marketing" in c["domain_scores"]
        assert c["avg_score"] > 0

    @patch(AUTH_PATCH_TARGET, side_effect=_mock_company_auth)
    def test_candidates_sorted_by_score(self, _mock):
        _sessions.clear()
        _create_session_with_answers("marketing", count=1, user_id="cand-low")
        _create_session_with_answers("marketing", count=2, user_id="cand-high")

        r = client.get("/api/company/candidates", headers={"Authorization": "Bearer tok"})
        candidates = r.json()["candidates"]
        assert candidates[0]["avg_score"] >= candidates[-1]["avg_score"]


# ── Compare ───────────────────────────────────────────────────────────────────

class TestCompanyCompare:
    @patch(AUTH_PATCH_TARGET, side_effect=_mock_company_auth)
    def test_compare_sessions(self, _mock):
        _sessions.clear()
        s1 = _create_session_with_answers("marketing", count=2)
        s2 = _create_session_with_answers("finance", count=2)

        r = client.get(f"/api/company/compare?session_ids={s1},{s2}", headers={"Authorization": "Bearer tok"})
        assert r.status_code == 200
        body = r.json()
        assert len(body["comparisons"]) == 2
        assert body["comparisons"][0]["rank"] == 1

    @patch(AUTH_PATCH_TARGET, side_effect=_mock_company_auth)
    def test_compare_needs_two(self, _mock):
        _sessions.clear()
        s1 = _create_session_with_answers("marketing", count=1)

        r = client.get(f"/api/company/compare?session_ids={s1}", headers={"Authorization": "Bearer tok"})
        assert r.status_code == 422

    @patch(AUTH_PATCH_TARGET, side_effect=_mock_company_auth)
    def test_compare_session_not_found(self, _mock):
        r = client.get("/api/company/compare?session_ids=fake1,fake2", headers={"Authorization": "Bearer tok"})
        assert r.status_code == 404


# ── Invite ────────────────────────────────────────────────────────────────────

class TestCompanyInvite:
    @patch(AUTH_PATCH_TARGET, side_effect=_mock_company_auth)
    def test_invite_creates_token(self, _mock):
        r = client.post("/api/company/invite", json={
            "email": "candidate@example.com",
            "domain_slug": "marketing",
            "question_count": 5,
        }, headers={"Authorization": "Bearer tok"})
        assert r.status_code == 200
        body = r.json()
        assert "invite_token" in body
        assert body["email"] == "candidate@example.com"
        assert body["domain"] == "marketing"
        assert body["created_by"] == "company-001"

    @patch(AUTH_PATCH_TARGET, side_effect=_mock_company_auth)
    def test_invite_invalid_domain(self, _mock):
        r = client.post("/api/company/invite", json={
            "email": "candidate@example.com",
            "domain_slug": "nonexistent",
        }, headers={"Authorization": "Bearer tok"})
        assert r.status_code == 404

    @patch(AUTH_PATCH_TARGET, side_effect=_mock_company_auth)
    def test_invite_default_question_count(self, _mock):
        r = client.post("/api/company/invite", json={
            "email": "candidate@example.com",
            "domain_slug": "finance",
        }, headers={"Authorization": "Bearer tok"})
        assert r.status_code == 200
        assert r.json()["question_count"] == 5
