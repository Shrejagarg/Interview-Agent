"""Authentication endpoints — Supabase Auth integration"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from typing import Optional
import os

router = APIRouter()

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")


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


@router.post("/register", response_model=AuthResponse)
def register(req: RegisterRequest):
    """Register a new user via Supabase Auth."""
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        raise HTTPException(
            status_code=503,
            detail="Supabase not configured. Set SUPABASE_URL and SUPABASE_ANON_KEY."
        )

    import httpx

    response = httpx.post(
        f"{SUPABASE_URL}/auth/v1/signup",
        json={
            "email": req.email,
            "password": req.password,
            "data": {
                "full_name": req.full_name,
                "role": req.role,
            }
        },
        headers={
            "apikey": SUPABASE_ANON_KEY,
            "Content-Type": "application/json",
        }
    )

    if response.status_code != 200:
        detail = response.json().get("msg", "Registration failed")
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
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        raise HTTPException(
            status_code=503,
            detail="Supabase not configured. Set SUPABASE_URL and SUPABASE_ANON_KEY."
        )

    import httpx

    response = httpx.post(
        f"{SUPABASE_URL}/auth/v1/token?grant_type=password",
        json={
            "email": req.email,
            "password": req.password,
        },
        headers={
            "apikey": SUPABASE_ANON_KEY,
            "Content-Type": "application/json",
        }
    )

    if response.status_code != 200:
        detail = response.json().get("msg", "Login failed")
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


@router.get("/me")
def get_current_user():
    """Get current user profile (placeholder — requires JWT verification)."""
    return {"message": "TODO: Implement JWT verification with Supabase"}
