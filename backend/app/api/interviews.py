"""Interview endpoints — start, answer, and complete interviews"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from backend.app.domains import get_registry
import uuid
from datetime import datetime

router = APIRouter()

# In-memory session store (will be replaced with Supabase)
_sessions: Dict[str, Dict[str, Any]] = {}


class StartInterviewRequest(BaseModel):
    domain_slug: str
    question_count: int = 5
    resume_data: Optional[Dict[str, Any]] = None


class AnswerRequest(BaseModel):
    session_id: str
    question_id: str
    answer_text: str


class InterviewQuestion(BaseModel):
    id: str
    topic: str
    difficulty: str
    question: str
    index: int
    total: int


@router.post("/start")
def start_interview(req: StartInterviewRequest):
    """Start a new interview session."""
    registry = get_registry()
    domain = registry.get(req.domain_slug)
    if not domain:
        raise HTTPException(status_code=404, detail=f"Domain '{req.domain_slug}' not found")

    session_id = str(uuid.uuid4())
    questions = domain.get_questions()

    import random
    random.shuffle(questions)
    selected = questions[:req.question_count]

    _sessions[session_id] = {
        "id": session_id,
        "domain_slug": req.domain_slug,
        "questions": selected,
        "current_index": 0,
        "answers": [],
        "topic_scores": {},
        "started_at": datetime.now().isoformat(),
        "finished_at": None,
        "status": "in_progress",
    }

    first_q = selected[0] if selected else None

    return {
        "session_id": session_id,
        "domain": req.domain_slug,
        "question_count": len(selected),
        "current_question": {
            "id": first_q["id"],
            "topic": first_q["topic"],
            "difficulty": first_q["difficulty"],
            "question": first_q["question"],
            "index": 1,
            "total": len(selected),
        } if first_q else None,
    }


@router.get("/{session_id}/question")
def get_current_question(session_id: str):
    """Get the current question for a session."""
    session = _sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session["status"] == "completed":
        raise HTTPException(status_code=400, detail="Interview already completed")

    idx = session["current_index"]
    if idx >= len(session["questions"]):
        session["status"] = "completed"
        session["finished_at"] = datetime.now().isoformat()
        raise HTTPException(status_code=400, detail="No more questions")

    q = session["questions"][idx]
    return {
        "id": q["id"],
        "topic": q["topic"],
        "difficulty": q["difficulty"],
        "question": q["question"],
        "index": idx + 1,
        "total": len(session["questions"]),
    }


@router.post("/{session_id}/answer")
def submit_answer(session_id: str, req: AnswerRequest):
    """Submit an answer for the current question."""
    session = _sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session["status"] == "completed":
        raise HTTPException(status_code=400, detail="Interview already completed")

    idx = session["current_index"]
    if idx >= len(session["questions"]):
        raise HTTPException(status_code=400, detail="No more questions")

    q = session["questions"][idx]

    evaluation = {
        "answer": req.answer_text,
        "question_id": q["id"],
        "topic": q["topic"],
        "timestamp": datetime.now().isoformat(),
    }

    session["answers"].append(evaluation)
    session["current_index"] += 1

    has_more = session["current_index"] < len(session["questions"])
    next_q = None
    if has_more:
        nq = session["questions"][session["current_index"]]
        next_q = {
            "id": nq["id"],
            "topic": nq["topic"],
            "difficulty": nq["difficulty"],
            "question": nq["question"],
            "index": session["current_index"] + 1,
            "total": len(session["questions"]),
        }

    if not has_more:
        session["status"] = "completed"
        session["finished_at"] = datetime.now().isoformat()

    return {
        "session_id": session_id,
        "answer_recorded": True,
        "has_next": has_more,
        "next_question": next_q,
        "progress": f"{session['current_index']}/{len(session['questions'])}",
    }


@router.get("/{session_id}/report")
def get_report(session_id: str):
    """Get the interview report."""
    session = _sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return {
        "session_id": session_id,
        "domain": session["domain_slug"],
        "status": session["status"],
        "questions_total": len(session["questions"]),
        "answers_submitted": len(session["answers"]),
        "started_at": session["started_at"],
        "finished_at": session["finished_at"],
    }


@router.get("")
def list_sessions():
    """List all sessions."""
    return {
        "sessions": [
            {
                "id": s["id"],
                "domain": s["domain_slug"],
                "status": s["status"],
                "started_at": s["started_at"],
            }
            for s in _sessions.values()
        ]
    }
