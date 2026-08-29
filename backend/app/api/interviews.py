"""Interview endpoints — start, answer, and complete interviews with LLM evaluation

Uses core/engine.py (InterviewEngine) as the stateless brain.
Backend-specific: session management, resume upload, REST serialization.
Sessions are persisted to Supabase via backend.app.db.sessions.
"""

import logging
from typing import Dict, List, Any, Optional, Union

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, BackgroundTasks
from pydantic import BaseModel

from backend.app.domains import get_registry
from backend.app.api.auth import get_optional_user, UserProfile
from backend.app.api.webhooks import dispatch_webhooks
from backend.app.db.sessions import save_session_db, load_session_db, get_user_sessions_db, get_all_sessions_db
from backend.app.services.speech import transcribe_audio, generate_speech_base64

from core.engine import InterviewEngine
from core.state import create_interview_state
from core.config import get_config

logger = logging.getLogger(__name__)
router = APIRouter()

engine = InterviewEngine()
cfg = get_config()

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
    answer_time_seconds: Optional[float] = None


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

@router.post("/audio-start")
def start_interview_audio(
    req: StartInterviewRequest,
    user: Optional[UserProfile] = Depends(get_optional_user),
):
    """Starts the interview and returns the first question as TTS audio"""
    res = start_interview(req, user)
    
    # Generate TTS for the first question
    audio_b64 = None
    if res.get("current_question") and res["current_question"].get("question"):
        audio_b64 = generate_speech_base64(res["current_question"]["question"])
        
    res["audio_base64"] = audio_b64
    return res

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
        role_context=None,
        user_id=user.user_id if user else "anonymous",
        mode=req.mode
    )

    # 2. Start Interview via Engine
    state = engine.start_interview(state, resume_data=resume_data, question_count=req.question_count)

    # 3. Persist to DB
    session_id = state["session_id"]
    q_data = engine.get_next_question(state)
    save_session_db(state)

    return {
        "session_id": session_id,
        "domain": req.domain_slug,
        "experience_level": experience_level,
        "question_count": state["total_questions"],
        "current_question": _format_question_response(state, q_data)
    }


@router.get("/{session_id}/question")
def get_current_question(session_id: str):
    state = load_session_db(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Session not found")

    if state["status"] == "completed":
        raise HTTPException(status_code=400, detail="Interview already completed")

    q_data = engine.get_next_question(state)
    if not q_data:
        raise HTTPException(status_code=400, detail="No more questions")

    return _format_question_response(state, q_data)


@router.post("/{session_id}/audio-answer")
async def submit_audio_answer(
    session_id: str,
    question_id: str = Form(...),
    audio: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """Submit an answer via a recorded audio blob, transcribed to text, and get the next question as TTS."""
    audio_bytes = await audio.read()
    
    # Transcribe
    answer_text = transcribe_audio(audio_bytes, filename=audio.filename)
    
    # Delegate to the standard submit_answer text endpoint logic
    req = AnswerRequest(question_id=question_id, answer_text=answer_text, answer_time_seconds=0)
    res = submit_answer(session_id, req, background_tasks)
    
    # The submit_answer response either has a "next_question" (standard) or a "follow_up" (requires_followup)
    text_to_speak = None
    if res.get("follow_up"):
        text_to_speak = res["follow_up"]
    elif res.get("next_question") and res["next_question"].get("question"):
        text_to_speak = res["next_question"]["question"]
        
    audio_b64 = None
    if text_to_speak:
        audio_b64 = generate_speech_base64(text_to_speak)
        
    res["audio_base64"] = audio_b64
    res["transcribed_text"] = answer_text
    
    return res


@router.post("/{session_id}/answer")
def submit_answer(session_id: str, req: AnswerRequest, background_tasks: BackgroundTasks):
    state = load_session_db(session_id)
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

    requires_followup = (state["status"] == "awaiting_followup")

    next_q = None
    if not requires_followup:
        next_q_data = engine.get_next_question(state)
        next_q = _format_question_response(state, next_q_data)

    save_session_db(state)

    if state["status"] == "completed" and state.get("company_id"):
        background_tasks.add_task(dispatch_webhooks, state["company_id"], state)

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
def submit_followup(session_id: str, req: FollowupRequest, background_tasks: BackgroundTasks):
    state = load_session_db(session_id)
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

    save_session_db(state)

    if state["status"] == "completed" and state.get("company_id"):
        background_tasks.add_task(dispatch_webhooks, state["company_id"], state)

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
    state = load_session_db(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Session not found")

    # Make sure session is finalized if completed
    if state["status"] == "completed" and "_avg" not in state:
        from core.state import finalize_topics, get_average
        finalize_topics(state)
        state["_avg"] = get_average(state)

    per_answer = []
    total_answer_time = 0
    total_eval_time = 0
    for a in state.get("answers", []):
        timing = a.get("timing", {})
        total_answer_time += timing.get("answer_time_seconds", 0)
        total_eval_time += timing.get("eval_time_seconds", 0)
        per_answer.append({
            "question": a.get("question"),
            "topic": a.get("topic"),
            "difficulty": a.get("difficulty", "?"),
            "answer": a.get("answer"),
            "score": a.get("evaluation", {}).get("overall_score", 0),
            "strengths": a.get("evaluation", {}).get("strengths", []),
            "weaknesses": a.get("evaluation", {}).get("weaknesses", []),
        })

    recommendations = []
    for topic, avg in state.get("topic_scores", {}).items():
        if avg < cfg["verdicts"]["average_threshold"]:
            try:
                registry = get_registry()
                domain = registry.get(state["domain"])
                if domain:
                    rec = domain.get_recommendation(topic, avg)
                    recommendations.append({"topic": topic, "score": avg, "recommendation": rec})
            except Exception:
                pass

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
        "recommendations": recommendations,
        "answers": per_answer,
        "timing": {
            "total_answer_time": round(total_answer_time, 2),
            "total_eval_time": round(total_eval_time, 2),
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
    sessions = get_all_sessions_db()

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
