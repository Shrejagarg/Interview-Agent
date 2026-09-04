"""Endpoint tests for the ARC IV custom question-bank API (mounted at /api/company).

Runs against the throwaway temp DB bound by conftest's DATABASE_URL override, so
the dev database is never touched. Users are seeded directly (no bcrypt) and JWTs
are minted via the same code path the real auth flow uses.
"""

import uuid

from fastapi.testclient import TestClient

from backend.app import app
from backend.app.api.auth import _make_token
from backend.app.db import database
from backend.app.db.models import User
from backend.tests import conftest  # noqa: F401  (temp-DB quarantine)

client = TestClient(app)


def _seed_user(role: str) -> str:
    user_id = str(uuid.uuid4())
    email = f"{role}_{uuid.uuid4().hex[:8]}@test.com"
    with database.SessionLocal() as db:
        db.add(User(id=user_id, email=email, password_hash="x", role=role, full_name=role))
        db.commit()
    return _make_token(user_id, role)


def _fresh_bank_tables():
    from sqlalchemy import text
    with database.engine.begin() as conn:
        conn.execute(text("DELETE FROM custom_questions"))
        conn.execute(text("DELETE FROM custom_question_banks"))


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


class TestCustomBankEndpoints:
    def test_company_crud_flow(self):
        _fresh_bank_tables()
        t = _seed_user("company")
        h = _auth(t)

        # create
        r = client.post("/api/company/banks", json={
            "name": "My Bank", "domain_slug": "marketing", "description": "desc"
        }, headers=h)
        assert r.status_code == 201
        bank_id = r.json()["id"]

        # list
        r = client.get("/api/company/banks", headers=h)
        assert r.status_code == 200
        assert any(b["id"] == bank_id for b in r.json()["banks"])

        # get
        r = client.get(f"/api/company/banks/{bank_id}", headers=h)
        assert r.status_code == 200
        assert r.json()["question_count"] == 0

        # update
        r = client.put(f"/api/company/banks/{bank_id}", json={"name": "Renamed"}, headers=h)
        assert r.status_code == 200
        assert r.json()["name"] == "Renamed"

        # add question
        r = client.post(f"/api/company/banks/{bank_id}/questions", json={
            "topic": "seo", "difficulty": "medium", "question_text": "What is SEO?"
        }, headers=h)
        assert r.status_code == 201
        qid = r.json()["id"]

        # update question
        r = client.put(f"/api/company/banks/{bank_id}/questions/{qid}", json={"difficulty": "hard"},
                       headers=h)
        assert r.status_code == 200
        assert r.json()["difficulty"] == "hard"

        # delete question
        r = client.delete(f"/api/company/banks/{bank_id}/questions/{qid}", headers=h)
        assert r.status_code == 204

        # delete bank
        r = client.delete(f"/api/company/banks/{bank_id}", headers=h)
        assert r.status_code == 204
        assert client.get(f"/api/company/banks/{bank_id}", headers=h).status_code == 404

    def test_get_missing_bank_404(self):
        _fresh_bank_tables()
        t = _seed_user("company")
        h = _auth(t)
        assert client.get("/api/company/banks/nope", headers=h).status_code == 404

    def test_update_missing_bank_404(self):
        _fresh_bank_tables()
        t = _seed_user("company")
        h = _auth(t)
        assert client.put("/api/company/banks/nope", json={"name": "x"}, headers=h).status_code == 404

    def test_delete_missing_bank_404(self):
        _fresh_bank_tables()
        t = _seed_user("company")
        h = _auth(t)
        assert client.delete("/api/company/banks/nope", headers=h).status_code == 404

    def test_add_question_to_missing_bank_404(self):
        _fresh_bank_tables()
        t = _seed_user("company")
        h = _auth(t)
        r = client.post("/api/company/banks/nope/questions", json={
            "topic": "x", "question_text": "Q?"
        }, headers=h)
        assert r.status_code == 404

    def test_update_question_missing_404(self):
        _fresh_bank_tables()
        t = _seed_user("company")
        h = _auth(t)
        r = client.put("/api/company/banks/nope/questions/nope", json={"topic": "x"}, headers=h)
        assert r.status_code == 404

    def test_company_cannot_touch_another_companys_bank(self):
        _fresh_bank_tables()
        t1 = _seed_user("company")
        h1 = _auth(t1)
        bank_id = client.post("/api/company/banks", json={
            "name": "Other", "domain_slug": "sales"
        }, headers=h1).json()["id"]

        t2 = _seed_user("company")
        h2 = _auth(t2)
        assert client.get(f"/api/company/banks/{bank_id}", headers=h2).status_code == 404
        assert client.put(f"/api/company/banks/{bank_id}", json={"name": "x"}, headers=h2).status_code == 404
        assert client.delete(f"/api/company/banks/{bank_id}", headers=h2).status_code == 404


class TestCustomRoleEnforcement:
    def test_candidate_forbidden(self):
        _fresh_bank_tables()
        t = _seed_user("candidate")
        h = _auth(t)
        assert client.get("/api/company/banks", headers=h).status_code == 403
        assert client.post("/api/company/banks", json={"name": "x", "domain_slug": "mkt"},
                           headers=h).status_code == 403

    def test_unauthenticated_401(self):
        _fresh_bank_tables()
        assert client.get("/api/company/banks").status_code == 401

    def test_malformed_token_401(self):
        _fresh_bank_tables()
        assert client.get("/api/company/banks", headers={"Authorization": "Bearer bogus"}).status_code == 401
