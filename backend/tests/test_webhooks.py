"""Tests for webhook endpoints — CRUD, URL validation, dispatch, delivery tracking"""

import sys
import os
import json
import hashlib
import hmac
from unittest.mock import patch, Mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from fastapi.testclient import TestClient
from backend.app import app
from backend.app.api import webhooks as webhooks_mod
from backend.app.api.auth import UserProfile

AUTH_PATCH_TARGET = "backend.app.api.auth.get_current_user"

COMPANY_USER = UserProfile(user_id="company-001", email="acme@corp.com", role="company", full_name="ACME Corp")
COMPANY_TWO = UserProfile(user_id="company-002", email="other@corp.com", role="company", full_name="Other Corp")
CANDIDATE_USER = UserProfile(user_id="cand-001", email="jane@example.com", role="candidate")


def _mock_company_auth(*args, **kwargs):
    return COMPANY_USER


def _mock_company_two_auth(*args, **kwargs):
    return COMPANY_TWO


def _mock_candidate_auth(*args, **kwargs):
    return CANDIDATE_USER


def _mock_llm(messages, *args, **kwargs):
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


client = TestClient(app)

_patches = [
    patch("core.evaluator._call_llm", side_effect=_mock_llm),
    patch("core.engine.pre_screen_answer", return_value={"pass": True, "auto_score": 0}),
]


def setup_module():
    for p in _patches:
        p.start()


def teardown_module():
    for p in _patches:
        p.stop()


def _register_webhook(url="https://example.com/ats/hook", events=None):
    resp = client.post("/api/webhooks", json={
        "url": url,
        "events": events if events is not None else ["interview.completed"],
        "description": "Production ATS",
    }, headers={"Authorization": "Bearer tok"})
    return resp


# ── URL Validation ────────────────────────────────────────────────────────────

class TestUrlValidation:
    def test_rejects_non_url(self):
        with _raises_422():
            webhooks_mod._validate_webhook_url("not-a-url", allow_private=False)

    def test_rejects_http_public(self):
        with _raises_422():
            webhooks_mod._validate_webhook_url("http://example.com/hook", allow_private=False)

    def test_rejects_loopback_when_not_allowed(self):
        with _raises_422():
            webhooks_mod._validate_webhook_url("https://127.0.0.1/hook", allow_private=False)

    def test_rejects_metadata_ip(self):
        with _raises_422():
            webhooks_mod._validate_webhook_url("https://169.254.169.254/latest/meta-data", allow_private=False)

    def test_allows_loopback_in_dev(self):
        assert webhooks_mod._validate_webhook_url("http://localhost:9000/hook", allow_private=True) == "http://localhost:9000/hook"

    def test_allows_https_public(self):
        assert webhooks_mod._validate_webhook_url("https://example.com/hook", allow_private=False) == "https://example.com/hook"


def _raises_422():
    from fastapi import HTTPException
    import pytest
    return pytest.raises(HTTPException) if hasattr(pytest, "raises") else _HTTPExceptionContext()


class _HTTPExceptionContext:
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc, tb):
        from fastapi import HTTPException
        if exc_type is None or not issubclass(exc_type, HTTPException):
            raise AssertionError("Expected HTTPException but none raised")
        if exc.status_code != 422:
            raise AssertionError(f"Expected 422, got {exc.status_code}")
        return True


# ── Create / List ─────────────────────────────────────────────────────────────

class TestCreateWebhook:
    @patch(AUTH_PATCH_TARGET, side_effect=_mock_company_auth)
    def test_create_returns_secret_once(self, _mock):
        r = _register_webhook()
        assert r.status_code == 200
        body = r.json()
        assert body["id"]
        assert body["url"] == "https://example.com/ats/hook"
        assert body["is_active"] is True
        assert body["events"] == ["interview.completed"]
        assert "secret" in body and len(body["secret"]) >= 32

    @patch(AUTH_PATCH_TARGET, side_effect=_mock_company_auth)
    def test_create_rejects_http(self, _mock):
        # patch env so dev-mode allowance is disabled
        with patch.object(webhooks_mod, "ENV", "production"), patch.object(webhooks_mod, "WEBHOOK_ALLOW_PRIVATE", False):
            r = _register_webhook(url="http://example.com/ats/hook")
        assert r.status_code == 422

    @patch(AUTH_PATCH_TARGET, side_effect=_mock_company_auth)
    def test_create_rejects_unsupported_event(self, _mock):
        r = _register_webhook(events=["interview.started"])
        assert r.status_code == 422

    @patch(AUTH_PATCH_TARGET, side_effect=_mock_company_auth)
    def test_create_rejects_empty_events(self, _mock):
        r = _register_webhook(events=[])
        assert r.status_code == 422

    @patch(AUTH_PATCH_TARGET, side_effect=_mock_candidate_auth)
    def test_candidate_cannot_create(self, _mock):
        r = _register_webhook()
        assert r.status_code == 403


class TestListWebhook:
    @patch(AUTH_PATCH_TARGET, side_effect=_mock_company_auth)
    def test_list_never_returns_secret(self, _mock):
        _register_webhook(url="https://one.example.com/hook")
        _register_webhook(url="https://two.example.com/hook")

        r = client.get("/api/webhooks", headers={"Authorization": "Bearer tok"})
        assert r.status_code == 200
        body = r.json()
        assert len(body["webhooks"]) == 2
        for wh in body["webhooks"]:
            assert "secret" not in wh

    @patch(AUTH_PATCH_TARGET, side_effect=_mock_company_auth)
    def test_get_never_returns_secret(self, _mock):
        created = _register_webhook().json()
        r = client.get(f"/api/webhooks/{created['id']}", headers={"Authorization": "Bearer tok"})
        assert r.status_code == 200
        body = r.json()
        assert "secret" not in body
        assert body["id"] == created["id"]

    @patch(AUTH_PATCH_TARGET, side_effect=_mock_company_auth)
    def test_get_owned_webhook(self, _mock):
        created = _register_webhook().json()
        r = client.get(f"/api/webhooks/{created['id']}", headers={"Authorization": "Bearer tok"})
        assert r.status_code == 200
        assert r.json()["url"] == created["url"]


# ── Ownership ─────────────────────────────────────────────────────────────────

class TestOwnership:
    @patch(AUTH_PATCH_TARGET, side_effect=_mock_company_auth)
    def test_create_under_company_001(self, _mock):
        created = _register_webhook().json()
        assert created["id"]

    @patch(AUTH_PATCH_TARGET, side_effect=_mock_company_auth)
    def test_other_company_cannot_view(self, _mock):
        created = _register_webhook().json()
        with patch(AUTH_PATCH_TARGET, side_effect=_mock_company_two_auth):
            r = client.get(f"/api/webhooks/{created['id']}", headers={"Authorization": "Bearer tok"})
        assert r.status_code == 403

    @patch(AUTH_PATCH_TARGET, side_effect=_mock_company_auth)
    def test_other_company_cannot_update(self, _mock):
        created = _register_webhook().json()
        with patch(AUTH_PATCH_TARGET, side_effect=_mock_company_two_auth):
            r = client.put(f"/api/webhooks/{created['id']}", json={"is_active": False},
                           headers={"Authorization": "Bearer tok"})
        assert r.status_code == 403

    @patch(AUTH_PATCH_TARGET, side_effect=_mock_company_auth)
    def test_other_company_cannot_delete(self, _mock):
        created = _register_webhook().json()
        with patch(AUTH_PATCH_TARGET, side_effect=_mock_company_two_auth):
            r = client.delete(f"/api/webhooks/{created['id']}", headers={"Authorization": "Bearer tok"})
        assert r.status_code == 403


# ── Update / Delete ───────────────────────────────────────────────────────────

class TestUpdateDelete:
    @patch(AUTH_PATCH_TARGET, side_effect=_mock_company_auth)
    def test_update_url_and_events(self, _mock):
        created = _register_webhook().json()
        r = client.put(f"/api/webhooks/{created['id']}", json={
            "url": "https://new.example.com/hook",
            "events": ["interview.completed"],
            "is_active": False,
            "description": "Updated ATS",
        }, headers={"Authorization": "Bearer tok"})
        assert r.status_code == 200
        body = r.json()
        assert body["url"] == "https://new.example.com/hook"
        assert body["is_active"] is False
        assert body["description"] == "Updated ATS"
        assert "secret" not in body

    @patch(AUTH_PATCH_TARGET, side_effect=_mock_company_auth)
    def test_update_invalid_event(self, _mock):
        created = _register_webhook().json()
        r = client.put(f"/api/webhooks/{created['id']}", json={"events": ["bogus"]},
                       headers={"Authorization": "Bearer tok"})
        assert r.status_code == 422

    @patch(AUTH_PATCH_TARGET, side_effect=_mock_company_auth)
    def test_delete(self, _mock):
        created = _register_webhook().json()
        r = client.delete(f"/api/webhooks/{created['id']}", headers={"Authorization": "Bearer tok"})
        assert r.status_code == 200
        assert r.json()["deleted"] is True

        r2 = client.get(f"/api/webhooks/{created['id']}", headers={"Authorization": "Bearer tok"})
        assert r2.status_code == 404

    @patch(AUTH_PATCH_TARGET, side_effect=_mock_company_auth)
    def test_update_not_found(self, _mock):
        r = client.put("/api/webhooks/does-not-exist", json={"is_active": False},
                       headers={"Authorization": "Bearer tok"})
        assert r.status_code == 404


# ── Test Delivery ─────────────────────────────────────────────────────────────

class TestTestDelivery:
    @patch(AUTH_PATCH_TARGET, side_effect=_mock_company_auth)
    def test_test_delivers_success(self, _mock):
        created = _register_webhook().json()
        with patch("backend.app.api.webhooks.httpx.post", return_value=Mock(status_code=200)) as m_post:
            r = client.post(f"/api/webhooks/{created['id']}/test", headers={"Authorization": "Bearer tok"})
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "delivered"
        assert body["attempts"] == 1
        assert body["response_status"] == 200
        m_post.assert_called_once()

    @patch(AUTH_PATCH_TARGET, side_effect=_mock_company_auth)
    def test_test_delivery_signed(self, _mock):
        created = _register_webhook().json()
        secret = created["secret"]
        captured = {}

        class FakeResp:
            status_code = 200
            text = "ok"

        def fake_post(url, **kwargs):
            captured["url"] = url
            captured["headers"] = kwargs.get("headers", {})
            captured["body"] = kwargs.get("content", "")
            return FakeResp()

        with patch("backend.app.api.webhooks.httpx.post", side_effect=fake_post):
            r = client.post(f"/api/webhooks/{created['id']}/test", headers={"Authorization": "Bearer tok"})
        assert r.status_code == 200

        assert captured["url"] == created["url"]
        sig_header = captured["headers"]["X-Webhook-Signature"]
        expected = "sha256=" + hmac.new(secret.encode(), captured["body"].encode(), hashlib.sha256).hexdigest()
        assert sig_header == expected
        assert captured["headers"]["X-Webhook-Event"] == "test"
        assert captured["headers"]["X-Webhook-Delivery-Id"]

    @patch(AUTH_PATCH_TARGET, side_effect=_mock_company_auth)
    def test_test_delivery_failure(self, _mock):
        created = _register_webhook().json()
        with patch("backend.app.api.webhooks.httpx.post", side_effect=ConnectionError("conn refused")):
            del_resp = client.post(f"/api/webhooks/{created['id']}/test", headers={"Authorization": "Bearer tok"})
        assert del_resp.status_code == 200
        body = del_resp.json()
        assert body["status"] == "failed"
        assert body["attempts"] == 1  # test endpoint uses max_retries=1
        assert "conn refused" in (body["error_message"] or "")

    @patch(AUTH_PATCH_TARGET, side_effect=_mock_company_auth)
    def test_delivery_history(self, _mock):
        created = _register_webhook().json()
        with patch("backend.app.api.webhooks.httpx.post", return_value=Mock(status_code=200)):
            client.post(f"/api/webhooks/{created['id']}/test", headers={"Authorization": "Bearer tok"})

        r = client.get(f"/api/webhooks/{created['id']}/deliveries", headers={"Authorization": "Bearer tok"})
        assert r.status_code == 200
        deliveries = r.json()["deliveries"]
        assert len(deliveries) == 1
        assert deliveries[0]["status"] == "delivered"
        assert deliveries[0]["event_type"] == "test"


# ── Payload Builder ───────────────────────────────────────────────────────────

class TestPayloadBuilder:
    def test_payload_structure(self):
        state = {
            "session_id": "sess-1",
            "domain": "marketing",
            "status": "completed",
            "started_at": "2026-08-27T10:00:00",
            "finished_at": "2026-08-27T10:10:00",
            "user_id": "cand-001",
            "_avg": 7.85,
            "verdict": "Strong",
            "topic_scores": {"seo": 8.0, "branding": 7.5},
            "strong_topics": ["seo"],
            "weak_topics": ["ppc"],
            "total_questions": 1,
            "answers": [{
                "question": "What is SEO?",
                "answer": "Search engine optimization...",
                "topic": "seo",
                "difficulty": "easy",
                "evaluation": {
                    "overall_score": 7.5,
                    "strengths": ["clear"],
                    "weaknesses": ["short"],
                },
            }],
        }
        payload = webhooks_mod._build_payload(state)

        assert payload["event"] == "interview.completed"
        assert payload["candidate"]["user_id"] == "cand-001"
        assert payload["result"]["overall_score"] == 7.85
        assert payload["result"]["verdict"] == "Strong"
        assert payload["result"]["topic_scores"]["seo"] == 8.0
        assert len(payload["transcript"]) == 1
        assert payload["transcript"][0]["score"] == 7.5
        assert payload["transcript"][0]["strengths"] == ["clear"]
        assert len(payload["transcript"]) == payload["result"]["questions_answered"]

    def test_payload_average_fallback(self):
        state = {
            "session_id": "sess-2",
            "domain": "marketing",
            "status": "completed",
            "answers": [
                {"evaluation": {"overall_score": 8.0}},
                {"evaluation": {"overall_score": 6.0}},
            ],
        }
        payload = webhooks_mod._build_payload(state)
        assert payload["result"]["overall_score"] == 7.0
        assert payload["transcript"][0]["score"] == 8.0

    def test_hmac_signature(self):
        body = b'{"hello": "world"}'
        secret = "super-secret"
        sig = webhooks_mod._sign_payload(secret, body.decode())
        expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        assert sig == expected


# ── Dispatch-on-completion integration ────────────────────────────────────────

class TestDispatchOnCompletion:
    def _start_company_session(self, sid="sess-dispatch", company_id="company-001"):
        resp = client.post("/api/interviews/start", json={
            "domain_slug": "marketing",
            "question_count": 1,
        }, headers={"Authorization": "Bearer tok"})
        from backend.tests.conftest import _mock_sessions
        session = _mock_sessions[resp.json()["session_id"]]
        session["user_id"] = "cand-001"
        session["company_id"] = company_id
        return resp.json()["session_id"]

    @patch(AUTH_PATCH_TARGET, side_effect=_mock_company_auth)
    @patch("backend.app.api.interviews.dispatch_webhooks")
    def test_dispatch_fires_on_completion(self, mock_dispatch, _auth):
        from backend.tests.conftest import _mock_sessions
        _mock_sessions.clear()
        sid = self._start_company_session(company_id="company-001")

        q = client.get(f"/api/interviews/{sid}/question", headers={"Authorization": "Bearer tok"}).json()
        r = client.post(f"/api/interviews/{sid}/answer", json={
            "question_id": q["id"],
            "answer_text": "A detailed answer that covers the key marketing points well.",
        }, headers={"Authorization": "Bearer tok"})
        assert r.status_code == 200
        assert r.json()["has_next"] is False

        args, kwargs = mock_dispatch.call_args
        assert args[0] == "company-001"
        assert args[1]["status"] == "completed"
        assert args[1]["company_id"] == "company-001"

    @patch(AUTH_PATCH_TARGET, side_effect=_mock_company_auth)
    @patch("backend.app.api.interviews.dispatch_webhooks")
    def test_no_dispatch_without_company(self, mock_dispatch, _auth):
        from backend.tests.conftest import _mock_sessions
        _mock_sessions.clear()
        resp = client.post("/api/interviews/start", json={
            "domain_slug": "marketing",
            "question_count": 1,
        }, headers={"Authorization": "Bearer tok"})
        sid = resp.json()["session_id"]

        q = client.get(f"/api/interviews/{sid}/question", headers={"Authorization": "Bearer tok"}).json()
        r = client.post(f"/api/interviews/{sid}/answer", json={
            "question_id": q["id"],
            "answer_text": "A detailed answer that covers the key marketing points well.",
        }, headers={"Authorization": "Bearer tok"})
        assert r.status_code == 200
        mock_dispatch.assert_not_called()

    @patch(AUTH_PATCH_TARGET, side_effect=_mock_company_auth)
    @patch("backend.app.api.interviews.dispatch_webhooks")
    def test_no_dispatch_while_incomplete(self, mock_dispatch, _auth):
        from backend.tests.conftest import _mock_sessions
        _mock_sessions.clear()
        resp = client.post("/api/interviews/start", json={
            "domain_slug": "marketing",
            "question_count": 2,
        }, headers={"Authorization": "Bearer tok"})
        sid = resp.json()["session_id"]
        _mock_sessions[sid]["user_id"] = "cand-001"
        _mock_sessions[sid]["company_id"] = "company-001"

        q = client.get(f"/api/interviews/{sid}/question", headers={"Authorization": "Bearer tok"}).json()
        r = client.post(f"/api/interviews/{sid}/answer", json={
            "question_id": q["id"],
            "answer_text": "A detailed answer covering the points well.",
        }, headers={"Authorization": "Bearer tok"})
        assert r.status_code == 200
        assert r.json()["has_next"] is True
        mock_dispatch.assert_not_called()