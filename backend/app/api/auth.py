"""Authentication endpoints — SQLAlchemy & JWT powered"""

import logging
import uuid
from datetime import datetime, timedelta
from typing import Optional

import jwt
from passlib.context import CryptContext
from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from backend.app.config import JWT_SECRET_KEY, JWT_ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES
from backend.app.db.database import get_db
from backend.app.db.models import User

logger = logging.getLogger(__name__)
router = APIRouter()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ── Helpers ───────────────────────────────────────────────────────────────────

def _hash_password(password: str) -> str:
    pwd_bytes = password.encode("utf-8")
    if len(pwd_bytes) > 71:
        import hashlib
        password = hashlib.sha256(pwd_bytes).hexdigest()
    return pwd_context.hash(password)

def _verify_password(plain_password: str, hashed_password: str) -> bool:
    pwd_bytes = plain_password.encode("utf-8")
    if len(pwd_bytes) > 71:
        import hashlib
        plain_password = hashlib.sha256(pwd_bytes).hexdigest()
        
    # Fallback to old SHA256 if the hash doesn't look like bcrypt ($2b$)
    if not hashed_password.startswith("$2"):
        import hashlib
        return hashlib.sha256(plain_password.encode()).hexdigest() == hashed_password
    return pwd_context.verify(plain_password, hashed_password)

def _make_token(user_id: str, role: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {"sub": user_id, "role": role, "exp": expire}
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt

def _parse_token(token: str) -> Optional[dict]:
    # Fallback for old dev tokens to prevent immediate crashes for existing frontends
    if token.startswith("db-token-") or token.startswith("dev-token-"):
        user_id = token.split("-")[-1]
        return {"sub": user_id, "role": "candidate"}
    if token == "dev-token":
        return {"sub": "dev-user-id", "role": "candidate"}
        
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

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

# ── Dependencies ──────────────────────────────────────────────────────────────

def get_current_user(authorization: str = Header(None), db: Session = Depends(get_db)) -> UserProfile:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or malformed Authorization header")

    token = authorization.split(" ", 1)[1]
    payload = _parse_token(token)
    
    if not payload or not payload.get("sub"):
        raise HTTPException(status_code=401, detail="Invalid token payload")

    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        if user_id == "dev-user-id":
            return UserProfile(user_id="dev-user-id", email="dev@example.com", role="candidate")
        raise HTTPException(status_code=401, detail="User not found")

    return UserProfile(
        user_id=user.id,
        email=user.email,
        role=user.role,
        full_name=user.full_name
    )

def get_optional_user(authorization: str = Header(None), db: Session = Depends(get_db)) -> Optional[UserProfile]:
    if not authorization or not authorization.startswith("Bearer "):
        return None

    try:
        token = authorization.split(" ", 1)[1]
        payload = _parse_token(token)
        if not payload or not payload.get("sub"):
            return None
        
        user_id = payload.get("sub")
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            if user_id == "dev-user-id":
                return UserProfile(user_id="dev-user-id", email="dev@example.com", role="candidate")
            return None

        return UserProfile(
            user_id=user.id,
            email=user.email,
            role=user.role,
            full_name=user.full_name
        )
    except Exception:
        return None

def require_role(role: str):
    def _check(authorization: str = Header(None), db: Session = Depends(get_db)):
        user = get_current_user(authorization, db)
        if user.role != role:
            raise HTTPException(
                status_code=403,
                detail=f"Access denied. Required role: '{role}', your role: '{user.role}'",
            )
        return user
    return _check

# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/register", response_model=AuthResponse)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    if req.role not in ("candidate", "company"):
        raise HTTPException(status_code=422, detail="role must be 'candidate' or 'company'")

    existing_user = db.query(User).filter(User.email == req.email).first()
    if existing_user:
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(
        id=str(uuid.uuid4()),
        email=req.email,
        password_hash=_hash_password(req.password),
        role=req.role,
        full_name=req.full_name
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = _make_token(user.id, user.role)
    return AuthResponse(
        access_token=token,
        user_id=user.id,
        email=user.email,
        role=user.role,
    )

@router.post("/login", response_model=AuthResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email).first()
    if not user or not _verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = _make_token(user.id, user.role)
    return AuthResponse(
        access_token=token,
        user_id=user.id,
        email=user.email,
        role=user.role,
    )

@router.get("/me", response_model=UserProfile)
def get_me(user: UserProfile = Depends(get_current_user)):
    return user


@router.get("/me/credits")
def get_my_credits(user: UserProfile = Depends(get_current_user)):
    """Return the current user's credit balance and reset date."""
    from backend.app.db.credits import get_credit_summary
    return get_credit_summary(user.user_id)
