"""Interview endpoints — start, answer, and complete interviews with LLM evaluation

Uses core/engine.py (InterviewEngine) as the stateless brain.
Backend-specific: session management, resume upload, REST serialization.
Sessions are persisted to Supabase via backend.app.db.sessions.
"""

import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Union

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, BackgroundTasks
from pydantic import BaseModel

from backend.app.domains import get_registry
from backend.app.api.auth import get_optional_user, UserProfile
from backend.app.api.webhooks import dispatch_webhooks
from backend.app.db.sessions import save_session_db, load_session_db, get_user_sessions_db, get_all_sessions_db
from backend.app.db.invites import get_invite_db, mark_invite_used_db
from backend.app.db.custom_banks import get_active_questions_db
from backend.app.services.speech import transcribe_audio, generate_speech_base64

from core.engine import InterviewEngine
from core.state import create_interview_state, get_integrity_score
from core.config import get_config
from core.custom_bank import get_questions_from_bank, bank_is_usable

logger = logging.getLogger(__name__)
router = APIRouter()

engine = InterviewEngine()
cfg = get_config()

# ── Hard-lock (termination) policy ────────────────────────────────────────────
# The interview is locked (terminated) once anti-cheat reaches a threshold. Any
# endpoint that advances the session rejects with 403 while locked, and the
# report surfaces status="locked" so the UI can show a terminated screen.
LOCK_SCORE_THRESHOLD = 50          # lock when integrity score drops below this
LOCK_SERIOUS_EVENT_COUNT = 3       # OR after this many tab_switch/face_lost events
SERIOUS_LOCK_EVENTS = ("tab_switch", "face_lost")


def _is_session_locked(state: Dict[str, Any]) -> bool:
    """A session is locked if it was explicitly marked, or it crosses a threshold."""
    if state.get("status") == "locked":
        return True
    if get_integrity_score(state) < LOCK_SCORE_THRESHOLD:
        return True
    serious = sum(
        1 for f in state.get("seriousness_flags", [])
        if f.get("event") in SERIOUS_LOCK_EVENTS
    )
    return serious >= LOCK_SERIOUS_EVENT_COUNT


def _ensure_not_locked(state: Dict[str, Any]) -> None:
    if _is_session_locked(state):
        raise HTTPException(status_code=403, detail="Interview locked due to integrity policy")

# ── Request / Response Models ─────────────────────────────────────────────────

class StartInterviewRequest(BaseModel):
    domain_slug: str
    question_count: int = 5
    experience_level: Optional[str] = None
    resume_data: Optional[Dict[str, Any]] = None
    mode: str = "mock"

class StartInterviewFromInviteRequest(BaseModel):
    token: str
    resume_data: Optional[Dict[str, Any]] = None
    mode: str = "mock"

class AnswerRequest(BaseModel):
    question_id: Union[str, int]
    answer_text: str
    answer_time_seconds: Optional[float] = None


class FollowupRequest(BaseModel):
    answer_text: str
    answer_time_seconds: Optional[float] = None


class IntegrityEventRequest(BaseModel):
    event_type: str  # tab_switch | blur | copy | paste | face_lost
    detail: Optional[str] = None


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

    # 1. Credit check (uncapped by default — just tracks usage)
    if user and user.user_id != "anonymous":
        from backend.app.db.credits import has_credits, deduct_credit
        if not has_credits(user.user_id):
            raise HTTPException(status_code=402, detail="Monthly interview credit limit reached.")

    # 2. Create Core State
    state = create_interview_state(
        domain_slug=req.domain_slug,
        role_context=None,
        user_id=user.user_id if user else "anonymous",
        mode=req.mode
    )

    # 3. Start Interview via Engine
    state = engine.start_interview(state, resume_data=resume_data, question_count=req.question_count)

    # 4. Persist to DB
    session_id = state["session_id"]
    q_data = engine.get_next_question(state)
    save_session_db(state)

    # 5. Deduct credit
    if user and user.user_id != "anonymous":
        from backend.app.db.credits import deduct_credit
        deduct_credit(user.user_id)

    return {
        "session_id": session_id,
        "domain": req.domain_slug,
        "experience_level": experience_level,
        "question_count": state["total_questions"],
        "current_question": _format_question_response(state, q_data)
    }

@router.get("/invite/{token}")
def get_invite(token: str):
    invite = get_invite_db(token)
    if not invite:
        raise HTTPException(status_code=404, detail="Invite not found")
    if invite.get("status") == "used":
        raise HTTPException(status_code=400, detail="Invite has already been used")
        
    registry = get_registry()
    domain = registry.get(invite["domain_slug"])
    
    return {
        "token": invite["token"],
        "domain_slug": invite["domain_slug"],
        "domain_name": domain.name if domain else "Unknown Domain",
        "question_count": invite.get("question_count", 5),
        "experience_level": invite.get("experience_level"),
        "status": invite.get("status")
    }

@router.post("/start-from-invite")
def start_interview_from_invite(req: StartInterviewFromInviteRequest, user: UserProfile = Depends(get_optional_user)):
    invite = get_invite_db(req.token)
    if not invite:
        raise HTTPException(status_code=404, detail="Invite not found")
    if invite.get("status") == "used":
        raise HTTPException(status_code=400, detail="Invite has already been used")
        
    registry = get_registry()
    domain = registry.get(invite["domain_slug"])
    if not domain:
        raise HTTPException(status_code=404, detail=f"Domain '{invite['domain_slug']}' not found")

    experience_level = invite.get("experience_level") or "unknown"
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
    elif experience_level != "unknown":
        resume_data["experience_level"] = experience_level

    user_id = user.user_id if user else f"candidate_{req.token[:8]}"

    # 1. Resolve custom question bank (if invite has one)
    custom_questions = None
    bank_name = None
    bank_id = invite.get("bank_id")
    if bank_id:
        raw_questions = get_active_questions_db(bank_id)
        if bank_is_usable(raw_questions):
            question_count = invite.get("question_count", 5)
            custom_questions = get_questions_from_bank(
                raw_questions,
                count=question_count,
                experience_level=experience_level,
            )
            bank_name = invite.get("bank_name")  # populated by get_invite_db if joined
            logger.info("Using custom bank '%s' (%d questions) for invite %s", bank_id, len(custom_questions), req.token)
        else:
            logger.warning("Custom bank '%s' is empty — falling back to domain bank.", bank_id)

    # 2. Create Core State
    state = create_interview_state(
        domain_slug=invite["domain_slug"],
        role_context=None,
        user_id=user_id,
        mode=req.mode
    )
    state["company_id"] = invite.get("company_id")
    if bank_id:
        state["bank_id"] = bank_id

    # 3. Start Interview via Engine
    question_count = invite.get("question_count", 5)
    state = engine.start_interview(
        state,
        resume_data=resume_data,
        question_count=question_count,
        questions=custom_questions,   # custom_questions is None → falls back to domain bank
    )

    # 4. Persist to DB and mark invite as used
    session_id = state["session_id"]
    q_data = engine.get_next_question(state)
    save_session_db(state)
    mark_invite_used_db(req.token, session_id)

    response = {
        "session_id": state["session_id"],
        "domain": invite["domain_slug"],
        "experience_level": experience_level,
        "question_count": state["total_questions"],
        "current_question": _format_question_response(state, q_data),
    }
    if bank_name:
        response["bank_name"] = bank_name
    return response
@router.get("/{session_id}/question")
def get_current_question(session_id: str):
    state = load_session_db(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Session not found")

    _ensure_not_locked(state)

    if state["status"] == "completed":
        raise HTTPException(status_code=400, detail="Interview already completed")

    q_data = engine.get_next_question(state)
    if not q_data:
        raise HTTPException(status_code=400, detail="No more questions")

    return _format_question_response(state, q_data)


@router.post("/{session_id}/audio-answer")
async def submit_audio_answer(
    session_id: str,
    background_tasks: BackgroundTasks,
    audio: UploadFile = File(...),
    question_id: Optional[str] = Form(None)
):
    """Submit an answer via a recorded audio blob, transcribed to text, and get the next question as TTS."""
    audio_bytes = await audio.read()

    # Validate the session before spending a transcription call.
    state = load_session_db(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Session not found")

    _ensure_not_locked(state)

    # Transcribe
    answer_text = transcribe_audio(audio_bytes, filename=audio.filename)

    # Derive the current question id from session state when the client omits it
    if not question_id:
        current = state.get("current_question", {}) if state else {}
        question_id = str(current.get("id", ""))

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


@router.post("/{session_id}/audio-followup")
async def submit_audio_followup(
    session_id: str,
    background_tasks: BackgroundTasks,
    audio: UploadFile = File(...),
):
    audio_bytes = await audio.read()

    state = load_session_db(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Session not found")

    _ensure_not_locked(state)

    answer_text = transcribe_audio(audio_bytes, filename=audio.filename)
    
    req = FollowupRequest(answer_text=answer_text, answer_time_seconds=0)
    res = submit_followup(session_id, req, background_tasks)
    
    text_to_speak = None
    if res.get("next_question") and res["next_question"].get("question"):
        text_to_speak = res["next_question"]["question"]
        
    audio_b64 = None
    if text_to_speak:
        audio_b64 = generate_speech_base64(text_to_speak)
        
    res["audio_base64"] = audio_b64
    res["transcribed_text"] = answer_text
    
    return res


@router.post("/{session_id}/integrity-event")
def submit_integrity_event(
    session_id: str,
    req: IntegrityEventRequest,
    background_tasks: BackgroundTasks,
):
    """Record a passive anti-cheat event (tab switch, blur, copy, paste, face lost).

    Updates the session's warnings/seriousness_flags and returns the updated
    integrity score so the frontend can show live feedback to the candidate.
    """
    state = load_session_db(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Session not found")

    event = req.event_type.strip().lower()
    if event not in ("tab_switch", "blur", "copy", "paste", "face_lost"):
        raise HTTPException(status_code=422, detail=f"Unknown integrity event: {req.event_type}")

    current = state.get("current_question") or {}
    question_label = str(current.get("id", "unknown")) if isinstance(current, dict) else "unknown"

    # Severity mapping
    if event in ("tab_switch", "face_lost"):
        reason = "left_interview_window"
        severity = 15
    elif event == "blur":
        reason = "window_blur"
        severity = 10
    else:  # copy / paste
        reason = "clipboard_usage"
        severity = 10

    # Only add one flag per reason per question to avoid saturating the score
    existing = {f"{f.get('reason')}:{f.get('question')}" for f in state.get("seriousness_flags", [])}
    flag_key = f"{reason}:{question_label}"
    if flag_key not in existing:
        state.setdefault("seriousness_flags", []).append({
            "reason": reason,
            "question": question_label,
            "event": event,
            "detail": req.detail,
            "timestamp": datetime.now().isoformat(),
            "severity": severity,
        })
        state.setdefault("warnings", []).append(f"Detected: {event.replace('_', ' ')} ({reason}) on question {question_label}")

    # Evaluate the hard-lock so a locked state persists and blocks further answers.
    locked = _is_session_locked(state)
    if locked:
        state["status"] = "locked"
        state.setdefault("locked_reason", "Integrity policy violated (score too low or repeated tab/face loss)")

    try:
        save_session_db(state)
    except Exception as e:
        logger.error("Failed to persist integrity event for %s: %s", session_id, e)
        raise HTTPException(status_code=500, detail="Failed to record integrity event")

    return {
        "event_type": event,
        "recorded": True,
        "integrity_score": get_integrity_score(state),
        "locked": locked,
        "locked_reason": state.get("locked_reason") if locked else None,
    }


@router.post("/{session_id}/answer")
def submit_answer(session_id: str, req: AnswerRequest, background_tasks: BackgroundTasks):
    state = load_session_db(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Session not found")

    _ensure_not_locked(state)

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

    evaluation = state.get("current_main_evaluation") if requires_followup else (state["answers"][-1]["evaluation"] if state["answers"] else {})
    follow_up = state.get("current_main_evaluation", {}).get("follow_up") if requires_followup else ""

    if state.get("mode") == "strict" and evaluation:
        eval_copy = dict(evaluation)
        eval_copy.pop("ideal_answer", None)
        eval_copy.pop("notes", None)
        evaluation = eval_copy

    return {
        "session_id": session_id,
        "answer_recorded": True,
        "evaluation": evaluation,
        "has_next": state["status"] != "completed",
        "next_question": next_q,
        "follow_up": follow_up,
        "progress": f"{state.get('question_index', 0)}/{state.get('total_questions', 0)}",
    }


@router.post("/{session_id}/followup")
def submit_followup(session_id: str, req: FollowupRequest, background_tasks: BackgroundTasks):
    state = load_session_db(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Session not found")

    _ensure_not_locked(state)

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

    followup_evaluation = state["answers"][-1].get("evaluation", {}).get("follow_up_score", {})
    if state.get("mode") == "strict" and followup_evaluation:
        eval_copy = dict(followup_evaluation)
        eval_copy.pop("notes", None)
        followup_evaluation = eval_copy

    return {
        "session_id": session_id,
        "followup_evaluation": followup_evaluation,
        "merged_score": state["answers"][-1]["evaluation"].get("overall_score", 0),
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
        "locked": _is_session_locked(state),
        "locked_reason": state.get("locked_reason"),
        "integrity_score": get_integrity_score(state),
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
