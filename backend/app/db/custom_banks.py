"""Custom Question Bank DB CRUD helpers."""

import logging
from typing import Optional
from datetime import datetime
import uuid

from backend.app.db.database import SessionLocal
from backend.app.db.models import CustomQuestionBank, CustomQuestion

logger = logging.getLogger(__name__)


# ── Banks ─────────────────────────────────────────────────────────────────────

def create_bank_db(company_id: str, name: str, domain_slug: str, description: Optional[str] = None) -> dict:
    with SessionLocal() as db:
        bank = CustomQuestionBank(
            id=str(uuid.uuid4()),
            company_id=company_id,
            name=name,
            domain_slug=domain_slug,
            description=description,
            created_at=datetime.utcnow(),
        )
        db.add(bank)
        db.commit()
        db.refresh(bank)
        return _bank_to_dict(bank, include_questions=False)


def list_banks_db(company_id: str) -> list[dict]:
    with SessionLocal() as db:
        banks = (
            db.query(CustomQuestionBank)
            .filter(CustomQuestionBank.company_id == company_id)
            .order_by(CustomQuestionBank.created_at.desc())
            .all()
        )
        return [_bank_to_dict(b, include_questions=False) for b in banks]


def get_bank_db(bank_id: str, company_id: Optional[str] = None) -> Optional[dict]:
    """Return bank with all questions. Optionally validate ownership."""
    with SessionLocal() as db:
        q = db.query(CustomQuestionBank).filter(CustomQuestionBank.id == bank_id)
        if company_id:
            q = q.filter(CustomQuestionBank.company_id == company_id)
        bank = q.first()
        if not bank:
            return None
        return _bank_to_dict(bank, include_questions=True)


def update_bank_db(bank_id: str, company_id: str, **fields) -> Optional[dict]:
    with SessionLocal() as db:
        bank = db.query(CustomQuestionBank).filter(
            CustomQuestionBank.id == bank_id,
            CustomQuestionBank.company_id == company_id,
        ).first()
        if not bank:
            return None
        for k, v in fields.items():
            if hasattr(bank, k) and v is not None:
                setattr(bank, k, v)
        db.commit()
        db.refresh(bank)
        return _bank_to_dict(bank, include_questions=False)


def delete_bank_db(bank_id: str, company_id: str) -> bool:
    with SessionLocal() as db:
        bank = db.query(CustomQuestionBank).filter(
            CustomQuestionBank.id == bank_id,
            CustomQuestionBank.company_id == company_id,
        ).first()
        if not bank:
            return False
        db.delete(bank)
        db.commit()
        return True


# ── Questions ─────────────────────────────────────────────────────────────────

def add_question_db(bank_id: str, company_id: str, topic: str, difficulty: str,
                    question_text: str, roles: Optional[list] = None) -> Optional[dict]:
    """Add a question; validates bank ownership via company_id."""
    with SessionLocal() as db:
        bank = db.query(CustomQuestionBank).filter(
            CustomQuestionBank.id == bank_id,
            CustomQuestionBank.company_id == company_id,
        ).first()
        if not bank:
            return None
        q = CustomQuestion(
            id=str(uuid.uuid4()),
            bank_id=bank_id,
            topic=topic,
            difficulty=difficulty,
            question_text=question_text,
            roles=roles or [],
            is_active=True,
        )
        db.add(q)
        db.commit()
        db.refresh(q)
        return _question_to_dict(q)


def update_question_db(question_id: str, bank_id: str, company_id: str, **fields) -> Optional[dict]:
    with SessionLocal() as db:
        q = (
            db.query(CustomQuestion)
            .join(CustomQuestionBank)
            .filter(
                CustomQuestion.id == question_id,
                CustomQuestion.bank_id == bank_id,
                CustomQuestionBank.company_id == company_id,
            )
            .first()
        )
        if not q:
            return None
        for k, v in fields.items():
            if hasattr(q, k) and v is not None:
                setattr(q, k, v)
        db.commit()
        db.refresh(q)
        return _question_to_dict(q)


def delete_question_db(question_id: str, bank_id: str, company_id: str) -> bool:
    with SessionLocal() as db:
        q = (
            db.query(CustomQuestion)
            .join(CustomQuestionBank)
            .filter(
                CustomQuestion.id == question_id,
                CustomQuestion.bank_id == bank_id,
                CustomQuestionBank.company_id == company_id,
            )
            .first()
        )
        if not q:
            return False
        db.delete(q)
        db.commit()
        return True


def get_active_questions_db(bank_id: str) -> list[dict]:
    """Return all active questions for a bank (used by the interview engine)."""
    with SessionLocal() as db:
        questions = (
            db.query(CustomQuestion)
            .filter(CustomQuestion.bank_id == bank_id, CustomQuestion.is_active == True)
            .all()
        )
        return [_question_to_dict(q) for q in questions]


# ── Serialisers ───────────────────────────────────────────────────────────────

def _bank_to_dict(bank: CustomQuestionBank, include_questions: bool = False) -> dict:
    d = {
        "id":          bank.id,
        "company_id":  bank.company_id,
        "name":        bank.name,
        "domain_slug": bank.domain_slug,
        "description": bank.description,
        "created_at":  bank.created_at.isoformat() if bank.created_at else None,
    }
    if include_questions:
        d["questions"] = [_question_to_dict(q) for q in (bank.questions or [])]
        d["question_count"] = len(d["questions"])
    else:
        d["question_count"] = 0  # caller can fetch separately
    return d


def _question_to_dict(q: CustomQuestion) -> dict:
    return {
        "id":            q.id,
        "bank_id":       q.bank_id,
        "topic":         q.topic,
        "difficulty":    q.difficulty,
        "roles":         q.roles or [],
        "question_text": q.question_text,
        "is_active":     q.is_active,
    }
