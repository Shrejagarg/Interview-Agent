"""Interview endpoints — start, answer, and complete interviews with LLM evaluation

Uses core/engine.py (InterviewEngine) as the stateless brain.
Backend-specific: session management, resume upload, REST serialization.
"""

import logging
import uuid
from typing import Dict, List, Any, Optional, Union

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from pydantic import BaseModel

from backend.app.domains import get_registry
from backend.app.api.auth import get_optional_user, UserProfile

from core.engine import InterviewEngine
from core.state import create_interview_state
from core.report import generate_report

logger = logging.getLogger(__name__)
router = APIRouter()

# In-memory session storage (Phase 1)
_sessions: Dict[str, Dict[str, Any]] = {}
engine = InterviewEngine()

# ── Request / Response Models ─────────────────────────────────────────────────

class StartInterviewRequest(BaseModel):
    domain_slug: str
    question_count: int = 5
    experience_level: Optional[str] = None
    resume_data: Optional[Dict[str, Any]] = None
    mode: str = "mock"


class AnswerRequest(BaseModel):
    question_id: Union[str, int]
    answer_text: str
    answer_time_seconds: Optional[int] = None


class FollowupRequest(BaseModel):
    answer_text: str
    answer_time_seconds: Optional[float] = None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _detect_experience_level(resume_data: Optional[Dict[str, Any]]) -> str:
    if not resume_data:
        return "unknown"
    return resume_data.get("experience_level", "unknown")


def _format_question_response(state: dict, q_data: dict) -> dict:
    if not q_data:
        return None
    if q_data["type"] == "followup":
        return {
            "is_followup": True,
            "question": q_data["question"]
        }
        
    q = q_data["question_data"]
    return {
        "id": q.get("id"),
        "topic": q.get("topic"),
        "difficulty": q.get("difficulty"),
        "question": q.get("question"),
        "index": state.get("question_index", 0),
        "total": state.get("total_questions", 0),
        "is_followup": False
    }


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/start")
def start_interview(
    req: StartInterviewRequest,
    user: Optional[UserProfile] = Depends(get_optional_user),
):
    registry = get_registry()
    domain = registry.get(req.domain_slug)
    if not domain:
        raise HTTPException(status_code=404, detail=f"Domain '{req.domain_slug}' not found")

    experience_level = req.experience_level or "unknown"
    resume_data = {}
    if req.resume_data:
        years = req.resume_data.get("years_experience")
        if years is not None:
            if int(years) < 2:
                experience_level = "fresher"
            elif int(years) > 5:
                experience_level = "senior"
            else:
                experience_level = "mid"
        
        resume_data = req.resume_data
        resume_data["experience_level"] = experience_level
    elif req.experience_level:
        resume_data["experience_level"] = experience_level
    
    # 1. Create Core State
    state = create_interview_state(
        domain_slug=req.domain_slug,
        role_context=None,  # Or parse from req if needed
        user_id=user.user_id if user else "anonymous",
        mode=req.mode
    )
    
    # 2. Start Interview via Engine
    state = engine.start_interview(state, resume_data=resume_data, question_count=req.question_count)
    
    # 3. Save to memory
    session_id = state["session_id"]
    _sessions[session_id] = state
    
    q_data = engine.get_next_question(state)
    _sessions[session_id] = state # Save state mutations from get_next_question
    
    return {
        "session_id": session_id,
        "domain": req.domain_slug,
        "experience_level": experience_level,
        "question_count": state["total_questions"],
        "current_question": _format_question_response(state, q_data)
    }


@router.get("/{session_id}/question")
def get_current_question(session_id: str):
    state = _sessions.get(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Session not found")

    if state["status"] == "completed":
        raise HTTPException(status_code=400, detail="Interview already completed")

    # The engine returns the *current* question if it's already set
    q_data = engine.get_next_question(state)
    if not q_data:
        raise HTTPException(status_code=400, detail="No more questions")
        
    return _format_question_response(state, q_data)


@router.post("/{session_id}/answer")
def submit_answer(session_id: str, req: AnswerRequest):
    state = _sessions.get(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Session not found")

    if state["status"] == "completed":
        raise HTTPException(status_code=400, detail="Interview already completed")

    if state["status"] == "awaiting_followup":
        raise HTTPException(status_code=422, detail="Must answer pending follow-up first")

    answer_text = req.answer_text.strip()
    if len(answer_text) < 5:
        raise HTTPException(status_code=422, detail="Answer too short (minimum 5 characters)")

    q = state.get("current_question", {})
    if q.get("id") and str(q.get("id")) != str(req.question_id):
        raise HTTPException(status_code=400, detail="Question ID mismatch")

    try:
        state = engine.submit_answer(state, answer_text, req.answer_time_seconds or 0)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Engine determines if followup is needed
    requires_followup = (state["status"] == "awaiting_followup")
    
    # If no followup, get next question
    next_q = None
    if not requires_followup:
        next_q_data = engine.get_next_question(state)
        next_q = _format_question_response(state, next_q_data)

    _sessions[session_id] = state

    return {
        "session_id": session_id,
        "answer_recorded": True,
        "evaluation": state.get("current_main_evaluation") if requires_followup else (state["answers"][-1]["evaluation"] if state["answers"] else {}),
        "has_next": state["status"] != "completed",
        "next_question": next_q,
        "follow_up": state.get("current_main_evaluation", {}).get("follow_up") if requires_followup else "",
        "progress": f"{state.get('question_index', 0)}/{state.get('total_questions', 0)}",
    }


@router.post("/{session_id}/followup")
def submit_followup(session_id: str, req: FollowupRequest):
    state = _sessions.get(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Session not found")

    if state["status"] != "awaiting_followup":
        raise HTTPException(status_code=422, detail="No pending follow-up question")

    answer_text = req.answer_text.strip()
    if len(answer_text) < 5:
        raise HTTPException(status_code=422, detail="Answer too short (minimum 5 characters)")

    try:
        state = engine.submit_followup(state, answer_text)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
        
    next_q_data = engine.get_next_question(state)
    next_q = _format_question_response(state, next_q_data)

    _sessions[session_id] = state

    last_ans = state["answers"][-1]

    return {
        "session_id": session_id,
        "followup_evaluation": last_ans["evaluation"].get("follow_up_score", {}),
        "merged_score": last_ans["evaluation"].get("overall_score", 0),
        "has_next": state["status"] != "completed",
        "next_question": next_q,
        "progress": f"{state.get('question_index', 0)}/{state.get('total_questions', 0)}",
    }


@router.get("/{session_id}/report")
def get_report(session_id: str):
    state = _sessions.get(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Session not found")

    # Make sure session is finalized if completed
    if state["status"] == "completed" and "_avg" not in state:
        from core.state import finalize_topics, get_average
        finalize_topics(state)
        state["_avg"] = get_average(state)

    per_answer = []
    for a in state.get("answers", []):
        per_answer.append({
            "question": a.get("question"),
            "topic": a.get("topic"),
            "difficulty": a.get("evaluation", {}).get("difficulty", "?"), # Engine may not store diff directly here, we might need to adjust
            "answer": a.get("answer"),
            "score": a.get("evaluation", {}).get("overall_score", 0),
            "strengths": a.get("evaluation", {}).get("strengths", []),
            "weaknesses": a.get("evaluation", {}).get("weaknesses", []),
        })

    return {
        "session_id": session_id,
        "domain": state["domain"],
        "experience_level": state.get("role_context", {}).get("experience_level", "unknown"),
        "status": state["status"],
        "started_at": state["started_at"],
        "finished_at": state.get("finished_at"),
        "questions_total": state.get("total_questions", 0),
        "answers_submitted": len(state.get("answers", [])),
        "overall_score": state.get("_avg", 0),
        "topic_scores": state.get("topic_scores", {}),
        "verdict": state.get("verdict", "Unknown"),
        "recommendations": [], # Could use generate_report to fill this
        "answers": per_answer,
        "timing": {
            "total_answer_time": 0, # Simplify for now
            "total_eval_time": 0,
        },
    }


@router.post("/parse-resume")
async def parse_resume_upload(file: UploadFile = File(...)):
    import os
    import tempfile

    suffix = os.path.splitext(file.filename or "")[1].lower()
    if suffix not in (".pdf", ".docx", ".txt", ".doc"):
        raise HTTPException(status_code=422, detail="Unsupported file format. Use PDF, DOCX, or TXT.")

    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=422, detail="File too large (max 10MB)")

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        from core.resume_parser import parse_resume
        result = parse_resume(tmp_path)
    except Exception as e:
        logger.error("Resume parsing failed: %s", e)
        raise HTTPException(status_code=422, detail=f"Failed to parse resume: {e}")
    finally:
        os.unlink(tmp_path)

    if result is None:
        raise HTTPException(status_code=422, detail="Could not extract any text from resume")

    skills_data = result.get("skills", {})
    experience_data = result.get("experience", {})
    quality_data = result.get("quality", {})
    education_data = result.get("education", {})

    return {
        "filename": file.filename,
        "name": result.get("name", ""),
        "skills": skills_data.get("skills", []),
        "skill_categories": skills_data.get("categories", []),
        "experience_level": result.get("experience_level", "unknown"),
        "years_experience": experience_data.get("years"),
        "job_titles": experience_data.get("job_titles", []),
        "education": education_data.get("entries", []),
        "quality_score": quality_data.get("score", 0),
        "quality_breakdown": quality_data.get("breakdown", {}),
    }


@router.get("")
def list_sessions(user: Optional[UserProfile] = Depends(get_optional_user)):
    sessions = list(_sessions.values())
    if user:
        sessions = [s for s in sessions if s.get("user_id") == user.user_id]

    return {
        "sessions": [
            {
                "id": s["session_id"],
                "domain": s["domain"],
                "status": s["status"],
                "started_at": s["started_at"],
                "answers": len(s.get("answers", [])),
            }
            for s in sessions
        ]
    }
