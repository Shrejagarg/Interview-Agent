"""Authentication endpoints — Supabase Auth with dev-mode mock fallback"""

import logging
import uuid
import hashlib
from typing import Optional, Dict

import httpx
from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel, EmailStr

from backend.app.config import (
    SUPABASE_URL,
    SUPABASE_ANON_KEY,
    ENV,
    is_supabase_configured,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Dev-mode in-memory user store ────────────────────────────────────────────

_dev_users: Dict[str, Dict[str, str]] = {}  # email -> {user_id, email, password_hash, role, full_name}


def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def _dev_create_user(email: str, password: str, role: str, full_name: Optional[str] = None) -> Dict[str, str]:
    user_id = str(uuid.uuid4())
    user = {
        "user_id": user_id,
        "email": email,
        "password_hash": _hash_password(password),
        "role": role,
        "full_name": full_name or "",
    }
    _dev_users[email] = user
    return user


def _dev_find_user(email: str) -> Optional[Dict[str, str]]:
    return _dev_users.get(email)


def _dev_verify_password(email: str, password: str) -> bool:
    user = _dev_users.get(email)
    if not user:
        return False
    return user["password_hash"] == _hash_password(password)


def _dev_make_token(user_id: str) -> str:
    return f"dev-token-{user_id}"


def _dev_parse_token(token: str) -> Optional[str]:
    if token.startswith("dev-token-"):
        return token[len("dev-token-"):]
    return None


# Seed a demo user on import
_dev_create_user("demo@candidate.com", "demo123", "candidate", "Demo Candidate")
_dev_create_user("demo@company.com", "demo123", "company", "Demo Company")


# ── Models ────────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    role: str = "candidate"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: str
    role: str


class UserProfile(BaseModel):
    user_id: str
    email: str
    role: str
    full_name: Optional[str] = None


# ── JWT Dependency ────────────────────────────────────────────────────────────

async def get_current_user(authorization: str = Header(None)) -> UserProfile:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or malformed Authorization header")

    token = authorization.split(" ", 1)[1]

    if not is_supabase_configured():
        if ENV == "development":
            user_id = _dev_parse_token(token)
            if user_id:
                for u in _dev_users.values():
                    if u["user_id"] == user_id:
                        return UserProfile(
                            user_id=u["user_id"],
                            email=u["email"],
                            role=u["role"],
                            full_name=u["full_name"],
                        )
            return UserProfile(
                user_id="dev-user-id",
                email="dev@example.com",
                role="candidate",
            )
        raise HTTPException(status_code=503, detail="Supabase not configured")

    try:
        response = httpx.get(
            f"{SUPABASE_URL}/auth/v1/user",
            headers={
                "apikey": SUPABASE_ANON_KEY,
                "Authorization": f"Bearer {token}",
            },
        )
        if response.status_code != 200:
            raise HTTPException(status_code=401, detail="Invalid or expired token")

        data = response.json()
        return UserProfile(
            user_id=data["id"],
            email=data["email"],
            role=data.get("app_metadata", {}).get("role", "candidate"),
            full_name=data.get("user_metadata", {}).get("full_name"),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("JWT verification failed: %s", e)
        raise HTTPException(status_code=401, detail="Token verification failed")


async def get_optional_user(authorization: str = Header(None)) -> Optional[UserProfile]:
    if not authorization or not authorization.startswith("Bearer "):
        return None

    token = authorization.split(" ", 1)[1]

    if not is_supabase_configured():
        if ENV == "development":
            user_id = _dev_parse_token(token)
            if user_id:
                for u in _dev_users.values():
                    if u["user_id"] == user_id:
                        return UserProfile(
                            user_id=u["user_id"],
                            email=u["email"],
                            role=u["role"],
                            full_name=u["full_name"],
                        )
            return UserProfile(
                user_id="dev-user-id",
                email="dev@example.com",
                role="candidate",
            )
        return None

    try:
        response = httpx.get(
            f"{SUPABASE_URL}/auth/v1/user",
            headers={
                "apikey": SUPABASE_ANON_KEY,
                "Authorization": f"Bearer {token}",
            },
        )
        if response.status_code != 200:
            return None

        data = response.json()
        return UserProfile(
            user_id=data["id"],
            email=data["email"],
            role=data.get("app_metadata", {}).get("role", "candidate"),
            full_name=data.get("user_metadata", {}).get("full_name"),
        )
    except Exception:
        return None


# ── Role-Based Access Control ─────────────────────────────────────────────────

def require_role(role: str):
    async def _check(authorization: str = Header(None)):
        user = await get_current_user(authorization)
        if user.role != role:
            raise HTTPException(
                status_code=403,
                detail=f"Access denied. Required role: '{role}', your role: '{user.role}'",
            )
        return user
    return _check


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/register", response_model=AuthResponse)
def register(req: RegisterRequest):
    if req.role not in ("candidate", "company"):
        raise HTTPException(status_code=422, detail="role must be 'candidate' or 'company'")

    if not is_supabase_configured():
        if ENV == "development":
            if _dev_find_user(req.email):
                raise HTTPException(status_code=409, detail="Email already registered")
            user = _dev_create_user(req.email, req.password, req.role, req.full_name)
            token = _dev_make_token(user["user_id"])
            return AuthResponse(
                access_token=token,
                user_id=user["user_id"],
                email=user["email"],
                role=user["role"],
            )
        raise HTTPException(
            status_code=503,
            detail="Supabase not configured. Set SUPABASE_URL and SUPABASE_ANON_KEY.",
        )

    response = httpx.post(
        f"{SUPABASE_URL}/auth/v1/signup",
        json={
            "email": req.email,
            "password": req.password,
            "data": {
                "full_name": req.full_name,
                "role": req.role,
            },
        },
        headers={
            "apikey": SUPABASE_ANON_KEY,
            "Content-Type": "application/json",
        },
    )

    if response.status_code != 200:
        try:
            detail = response.json().get("msg", "Registration failed")
        except Exception:
            detail = "Registration failed"
        raise HTTPException(status_code=response.status_code, detail=detail)

    data = response.json()
    return AuthResponse(
        access_token=data["access_token"],
        user_id=data["user"]["id"],
        email=data["user"]["email"],
        role=req.role,
    )


@router.post("/login", response_model=AuthResponse)
def login(req: LoginRequest):
    if not is_supabase_configured():
        if ENV == "development":
            if not _dev_verify_password(req.email, req.password):
                raise HTTPException(status_code=401, detail="Invalid email or password")
            user = _dev_find_user(req.email)
            token = _dev_make_token(user["user_id"])
            return AuthResponse(
                access_token=token,
                user_id=user["user_id"],
                email=user["email"],
                role=user["role"],
            )
        raise HTTPException(
            status_code=503,
            detail="Supabase not configured. Set SUPABASE_URL and SUPABASE_ANON_KEY.",
        )

    response = httpx.post(
        f"{SUPABASE_URL}/auth/v1/token?grant_type=password",
        json={
            "email": req.email,
            "password": req.password,
        },
        headers={
            "apikey": SUPABASE_ANON_KEY,
            "Content-Type": "application/json",
        },
    )

    if response.status_code != 200:
        try:
            detail = response.json().get("msg", "Login failed")
        except Exception:
            detail = "Login failed"
        raise HTTPException(status_code=response.status_code, detail=detail)

    data = response.json()
    user = data.get("user", {})
    role = user.get("app_metadata", {}).get("role", "candidate")

    return AuthResponse(
        access_token=data["access_token"],
        user_id=user["id"],
        email=user["email"],
        role=role,
    )


@router.get("/me", response_model=UserProfile)
async def get_me(user: UserProfile = Depends(get_current_user)):
    return user
