"""Regression tests for the invite-driven interview start flow.

Covers POST /api/interviews/start-from-invite for the two ownership modes:

- Logged-in candidate  -> the session is assigned to the candidate's
  ``user_id`` (NOT the anonymous ``candidate_<token>`` id).

  Regression guard: the UserProfile model exposes ``user_id`` (not ``id``).
  Using ``user.id`` here raised ``AttributeError: 'UserProfile' object has no
  attribute 'id'`` when a logged-in candidate started from an invite.

- Anonymous candidate -> the session falls back to ``candidate_<token>``.

LLM calls and session persistence are mocked (see conftest), and the invite is
written to the throwaway temp SQLite DB via ``create_invite_db`` — the dev
database is never touched.
"""

import uuid
import unittest.mock

from fastapi.testclient import TestClient

from backend.app import app
from backend.tests.conftest import _mock_sessions

client = TestClient(app)

_EMAIL = "candidate.invite@test.io"
_PASSWORD = "Passw0rd123!"
_DOMAIN = "marketing"


def _mock_llm(messages, *args, **kwargs):
    return {
        "message": {
            "content": '{"relevance":7,"clarity":6.5,"creativity":7.5,'
                        '"communication":7.2,"overall_score":7,'
                        '"strengths":["Good structure"],"weaknesses":["tbd"],'
                        '"ideal_answer":"","follow_up":"","is_serious":true,'
                        '"score":8}'
        }
    }


_patches = [
    ("core.evaluator._call_llm", _mock_llm),
    ("core.engine.pre_screen_answer", lambda answer, question: {"pass": True, "auto_score": 0}),
]


def setup_module():
    unittest.mock.patch("core.evaluator._call_llm", side_effect=_mock_llm).start()
    unittest.mock.patch(
        "core.engine.pre_screen_answer",
        side_effect=lambda answer, question: {"pass": True, "auto_score": 0},
    ).start()


def teardown_module():
    unittest.mock.patch.stopall()


def _create_invite(token: str) -> None:
    from backend.app.db.invites import create_invite_db
    create_invite_db({
        "token": token,
        "company_id": "comp-invite-test",
        "domain_slug": _DOMAIN,
        "question_count": 2,
        "experience_level": "mid",
        "status": "active",
    })


def _register_and_login() -> str:
    email = f"{uuid.uuid4().hex[:8]}@test.io"
    r = client.post("/api/auth/register", json={
        "email": email,
        "password": _PASSWORD,
        "role": "candidate",
        "full_name": "Invite Candidate",
    })
    assert r.status_code in (200, 201), r.text
    login = client.post("/api/auth/login", json={"email": email, "password": _PASSWORD})
    assert login.status_code == 200, login.text
    return login.json()["access_token"]


def test_invite_assigns_logged_in_user_id():
    """A logged-in candidate starts an invite interview with their own user_id."""
    token = _register_and_login()
    invite = "inv-logged-" + uuid.uuid4().hex[:6]
    _create_invite(invite)

    r = client.post(
        "/api/interviews/start-from-invite",
        json={"token": invite, "mode": "mock"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    session = _mock_sessions[body["session_id"]]
    # The session must be owned by the logged-in candidate, not an anonymous id.
    assert session["user_id"] != f"candidate_{invite[:8]}"
    assert session["user_id"] == _parse_user_id(token)


def test_invite_anonymous_uses_candidate_token_id():
    """Without auth the session falls back to the anonymous candidate_<token> id."""
    invite = "inv-anon-" + uuid.uuid4().hex[:6]
    _create_invite(invite)

    r = client.post(
        "/api/interviews/start-from-invite",
        json={"token": invite, "mode": "mock"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    session = _mock_sessions[body["session_id"]]
    assert session["user_id"] == f"candidate_{invite[:8]}"


def _parse_user_id(token: str) -> str:
    import jwt as pyjwt
    from backend.app.config import JWT_SECRET_KEY, JWT_ALGORITHM
    payload = pyjwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    return payload["sub"]
