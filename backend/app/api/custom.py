"""
api/custom.py — Company Custom Question Bank CRUD endpoints.

All routes require the authenticated user to have the 'company' role.
Mounted at /api/company in backend/app/__init__.py.
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from backend.app.api.auth import UserProfile, require_role
from backend.app.db.custom_banks import (
    create_bank_db, list_banks_db, get_bank_db,
    update_bank_db, delete_bank_db,
    add_question_db, update_question_db, delete_question_db,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Request / Response Models ─────────────────────────────────────────────────

class CreateBankRequest(BaseModel):
    name:        str
    domain_slug: str
    description: Optional[str] = None


class UpdateBankRequest(BaseModel):
    name:        Optional[str] = None
    description: Optional[str] = None


class CreateQuestionRequest(BaseModel):
    topic:         str
    difficulty:    str = "medium"   # easy | medium | hard
    question_text: str
    roles:         Optional[list[str]] = None


class UpdateQuestionRequest(BaseModel):
    topic:         Optional[str]  = None
    difficulty:    Optional[str]  = None
    question_text: Optional[str]  = None
    roles:         Optional[list[str]] = None
    is_active:     Optional[bool] = None


# ── Bank Endpoints ────────────────────────────────────────────────────────────

@router.get("/banks")
def list_banks(user: UserProfile = Depends(require_role("company"))):
    """List all custom question banks belonging to the authenticated company."""
    return {"banks": list_banks_db(user.user_id)}


@router.post("/banks", status_code=201)
def create_bank(req: CreateBankRequest, user: UserProfile = Depends(require_role("company"))):
    """Create a new custom question bank."""
    bank = create_bank_db(
        company_id=user.user_id,
        name=req.name,
        domain_slug=req.domain_slug,
        description=req.description,
    )
    return bank


@router.get("/banks/{bank_id}")
def get_bank(bank_id: str, user: UserProfile = Depends(require_role("company"))):
    """Get a bank with all its questions."""
    bank = get_bank_db(bank_id, company_id=user.user_id)
    if not bank:
        raise HTTPException(status_code=404, detail="Bank not found")
    return bank


@router.put("/banks/{bank_id}")
def update_bank(bank_id: str, req: UpdateBankRequest, user: UserProfile = Depends(require_role("company"))):
    """Update bank name or description."""
    bank = update_bank_db(bank_id, user.user_id, name=req.name, description=req.description)
    if not bank:
        raise HTTPException(status_code=404, detail="Bank not found")
    return bank


@router.delete("/banks/{bank_id}", status_code=204)
def delete_bank(bank_id: str, user: UserProfile = Depends(require_role("company"))):
    """Delete a bank and all its questions."""
    ok = delete_bank_db(bank_id, user.user_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Bank not found")


# ── Question Endpoints ────────────────────────────────────────────────────────

@router.post("/banks/{bank_id}/questions", status_code=201)
def add_question(bank_id: str, req: CreateQuestionRequest, user: UserProfile = Depends(require_role("company"))):
    """Add a question to a bank."""
    question = add_question_db(
        bank_id=bank_id,
        company_id=user.user_id,
        topic=req.topic,
        difficulty=req.difficulty,
        question_text=req.question_text,
        roles=req.roles,
    )
    if not question:
        raise HTTPException(status_code=404, detail="Bank not found or access denied")
    return question


@router.put("/banks/{bank_id}/questions/{question_id}")
def update_question(
    bank_id: str, question_id: str, req: UpdateQuestionRequest,
    user: UserProfile = Depends(require_role("company")),
):
    """Edit an existing question."""
    question = update_question_db(
        question_id=question_id,
        bank_id=bank_id,
        company_id=user.user_id,
        topic=req.topic,
        difficulty=req.difficulty,
        question_text=req.question_text,
        roles=req.roles,
        is_active=req.is_active,
    )
    if not question:
        raise HTTPException(status_code=404, detail="Question not found or access denied")
    return question


@router.delete("/banks/{bank_id}/questions/{question_id}", status_code=204)
def delete_question(bank_id: str, question_id: str, user: UserProfile = Depends(require_role("company"))):
    """Remove a question from a bank."""
    ok = delete_question_db(question_id, bank_id, user.user_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Question not found or access denied")
