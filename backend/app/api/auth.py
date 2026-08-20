"""Authentication endpoints — Supabase Auth integration with JWT verification"""

import logging
from typing import Optional

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
    """Verify the Supabase JWT and return the user profile.

    Falls back to a dev-mode bypass when Supabase is not configured.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or malformed Authorization header")

    token = authorization.split(" ", 1)[1]

    if not is_supabase_configured():
        if ENV == "development":
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
    """Like get_current_user, but returns None instead of raising when no token."""
    if not authorization or not authorization.startswith("Bearer "):
        return None

    token = authorization.split(" ", 1)[1]

    if not is_supabase_configured():
        if ENV == "development":
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
    """Create a dependency that requires the user to have a specific role."""
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
    """Register a new user via Supabase Auth."""
    if req.role not in ("candidate", "company"):
        raise HTTPException(status_code=422, detail="role must be 'candidate' or 'company'")

    if not is_supabase_configured():
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
    """Login via Supabase Auth."""
    if not is_supabase_configured():
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
    """Get the currently authenticated user's profile."""
    return user
