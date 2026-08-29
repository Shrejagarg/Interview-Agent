"""Tests for auth endpoints — register, login, /me plus JWT/token edge branches.

Uses the real temp-DB SQLAlchemy engine (DATABASE_URL override in conftest).
The autouse fixture wipes the `users` table before each test, so state is
isolated without touching the dev database.
"""

import uuid
import hashlib
from datetime import datetime, timedelta

import jwt
import pytest
from fastapi.testclient import TestClient

from backend.app import app
from backend.app.config import JWT_SECRET_KEY, JWT_ALGORITHM
from backend.app.api import auth as auth_mod
from backend.app.db.database import SessionLocal
from backend.app.db.models import User

client = TestClient(app)

PASSWORD = "Passw0rd123!"
EMAIL = "candidate@test.io"


def _register(email: str = EMAIL, password: str = PASSWORD, role: str = "candidate", full_name: str = None):
    body = {"email": email, "password": password, "role": role}
    if full_name:
        body["full_name"] = full_name
    return client.post("/api/auth/register", json=body)


class TestRegister:
    def test_register_candidate(self):
        r = _register()
        assert r.status_code == 200
        data = r.json()
        assert data["token_type"] == "bearer"
        assert data["email"] == EMAIL
        assert data["role"] == "candidate"
        assert data["access_token"]
        assert uuid.UUID(data["user_id"])

    def test_register_company_role(self):
        r = _register(email="company@test.io", role="company")
        assert r.status_code == 200
        assert r.json()["role"] == "company"

    def test_register_with_full_name(self):
        r = _register(full_name="Jane Doe")
        assert r.status_code == 200
        assert r.json()["user_id"]

    def test_register_duplicate_email_returns_409(self):
        assert _register().status_code == 200
        r = _register()
        assert r.status_code == 409

    def test_register_invalid_role_returns_422(self):
        r = _register(role="admin")
        assert r.status_code == 422

    def test_register_very_long_password_roundtrip(self):
        # bcrypt truncates at 72 bytes; the >71-byte path pre-hashes with sha256.
        long_pw = "x" * 80 + "!Aa1"
        assert _register(password=long_pw).status_code == 200
        r = client.post("/api/auth/login", json={"email": EMAIL, "password": long_pw})
        assert r.status_code == 200
        assert r.json()["email"] == EMAIL


class TestLogin:
    def test_login_success(self):
        _register()
        r = client.post("/api/auth/login", json={"email": EMAIL, "password": PASSWORD})
        assert r.status_code == 200
        data = r.json()
        assert data["token_type"] == "bearer"
        assert data["role"] == "candidate"

    def test_login_wrong_password_returns_401(self):
        _register()
        r = client.post("/api/auth/login", json={"email": EMAIL, "password": "wrong-password"})
        assert r.status_code == 401

    def test_login_unknown_email_returns_401(self):
        r = client.post("/api/auth/login", json={"email": "ghost@test.io", "password": PASSWORD})
        assert r.status_code == 401

    def test_legacy_sha256_hash_login(self):
        # Hashes without a $2 (bcrypt) prefix fall back to plain sha256 compare.
        hashed = hashlib.sha256(PASSWORD.encode()).hexdigest()
        with SessionLocal() as db:
            db.add(User(id=str(uuid.uuid4()), email=EMAIL,
                        password_hash=hashed, role="candidate"))
            db.commit()
        r = client.post("/api/auth/login", json={"email": EMAIL, "password": PASSWORD})
        assert r.status_code == 200


class TestMe:
    def test_me_with_valid_token(self):
        token = _register().json()["access_token"]
        r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        assert r.json()["email"] == EMAIL
        assert r.json()["role"] == "candidate"

    def test_me_without_header_returns_401(self):
        r = client.get("/api/auth/me")
        assert r.status_code == 401

    def test_me_with_malformed_header_returns_401(self):
        r = client.get("/api/auth/me", headers={"Authorization": "Basic abc"})
        assert r.status_code == 401

    def test_me_with_garbage_token_returns_401(self):
        r = client.get("/api/auth/me", headers={"Authorization": "Bearer not.a.jwt"})
        assert r.status_code == 401

    def test_me_with_expired_token_returns_401(self):
        _register()
        payload = {
            "sub": str(uuid.uuid4()),
            "role": "candidate",
            "exp": datetime.utcnow() - timedelta(minutes=1),
        }
        token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 401
        assert r.json()["detail"] == "Token has expired"

    def test_me_with_dev_token_returns_dev_user(self):
        r = client.get("/api/auth/me", headers={"Authorization": "Bearer dev-token"})
        assert r.status_code == 200
        assert r.json()["user_id"] == "dev-user-id"

    def test_me_with_db_token_prefix_for_missing_user_returns_401(self):
        # Covers the legacy "db-token-"/"dev-token-" prefix parse branch.
        token = "db-token-" + str(uuid.uuid4())
        r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 401


class TestTokenHelpers:
    def test_verify_password_hashed_non_bcrypt_rejects(self):
        # Hashed value that doesn't start with $2 and isn't a matching sha256.
        assert not auth_mod._verify_password("secret", "plainoldhash")

    def test_parse_token_expired_raises_http_401(self):
        from fastapi import HTTPException
        payload = {
            "sub": "u1",
            "role": "candidate",
            "exp": datetime.utcnow() - timedelta(hours=2),
        }
        token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        with pytest.raises(HTTPException) as exc:
            auth_mod._parse_token(token)
        assert exc.value.status_code == 401