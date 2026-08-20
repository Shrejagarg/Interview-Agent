"""Interview endpoints — start, answer, and complete interviews with LLM evaluation

Uses core/ package for evaluation logic (retry, weighted scoring, follow-ups).
Backend-specific: multi-domain question selection, session management, resume upload.
"""

import random
import logging
import uuid
import time
from datetime import datetime
from typing import Dict, List, Any, Optional

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from pydantic import BaseModel

from backend.app.domains import get_registry
from backend.app.domains.base import BaseDomain
from backend.app.api.auth import get_optional_user, UserProfile

from core.evaluator import _call_llm, _parse_json, _compute_weighted_score
from core.evaluator import evaluate_followup, merge

logger = logging.getLogger(__name__)
router = APIRouter()

_sessions: Dict[str, Dict[str, Any]] = {}


# ── Request / Response Models ─────────────────────────────────────────────────

class StartInterviewRequest(BaseModel):
    domain_slug: str
    question_count: int = 5
    experience_level: Optional[str] = None
    resume_data: Optional[Dict[str, Any]] = None


class AnswerRequest(BaseModel):
    question_id: str
    answer_text: str
    answer_time_seconds: Optional[float] = None


class FollowupRequest(BaseModel):
    answer_text: str
    answer_time_seconds: Optional[float] = None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _detect_experience_level(resume_data: Optional[Dict[str, Any]]) -> str:
    if not resume_data:
        return "mid"
    years = resume_data.get("years_experience", 0)
    if years <= 1:
        return "fresher"
    elif years <= 4:
        return "mid"
    return "senior"


def _select_questions(
    domain: BaseDomain,
    count: int,
    experience_level: str,
) -> List[Dict[str, Any]]:
    all_questions = domain.get_questions()
    distribution = domain.get_difficulty_distribution(experience_level)

    pool: List[Dict[str, Any]] = []
    for diff, ratio in distribution.items():
        diff_questions = [q for q in all_questions if q["difficulty"] == diff]
        pool.extend(diff_questions)

    random.shuffle(pool)

    if len(pool) < count:
        remaining = [q for q in all_questions if q not in pool]
        random.shuffle(remaining)
        pool.extend(remaining)

    return pool[:count]


def _evaluate_answer(
    domain: BaseDomain,
    question_text: str,
    answer_text: str,
) -> Dict[str, Any]:
    prompt = domain.get_evaluation_prompt(question_text, answer_text)

    try:
        response = _call_llm([{"role": "user", "content": prompt}])
    except Exception as e:
        logger.error("LLM call failed: %s", e)
        return _fallback_evaluation(answer_text)

    text = response["message"]["content"]

    try:
        parsed = _parse_json(text)
    except Exception as e:
        logger.error("Failed to parse LLM evaluation JSON: %s", e)
        return _fallback_evaluation(answer_text)

    if not parsed or not isinstance(parsed, dict):
        logger.warning("LLM returned unparseable evaluation, using fallback scores")
        return _fallback_evaluation(answer_text)

    defaults = {dim: 50 for dim in domain.scoring_dimensions}
    defaults.update({
        "overall_score": 50,
        "strengths": [],
        "weaknesses": [],
        "follow_up": "",
        "is_serious": True,
    })
    defaults.update(parsed)

    for dim in domain.scoring_dimensions:
        val = defaults.get(dim, 50)
        defaults[dim] = max(0, min(100, int(val)))

    defaults["overall_score"] = _compute_weighted_score(defaults)

    return defaults


def _fallback_evaluation(answer_text: str) -> Dict[str, Any]:
    text = answer_text.strip().lower()
    if not text or len(text) < 10:
        return {
            "overall_score": 10,
            "strengths": [],
            "weaknesses": ["Answer too short or empty"],
            "follow_up": "",
            "is_serious": False,
        }
    score = min(80, 30 + len(text) // 10)
    return {
        "overall_score": score,
        "strengths": ["Provided a response"],
        "weaknesses": ["Unable to verify with LLM"],
        "follow_up": "",
        "is_serious": True,
    }


def _compute_session_summary(session: Dict[str, Any], domain: BaseDomain) -> Dict[str, Any]:
    answers = session["answers"]
    if not answers:
        return {
            "overall_score": 0,
            "topic_scores": {},
            "verdict": "No answers submitted",
        }

    topic_buckets: Dict[str, List[int]] = {}
    for a in answers:
        topic = a.get("topic", "unknown")
        score = a.get("evaluation", {}).get("overall_score", 0)
        topic_buckets.setdefault(topic, []).append(score)

    topic_scores = {}
    for topic, scores in topic_buckets.items():
        topic_scores[topic] = round(sum(scores) / len(scores), 1)

    overall = round(
        sum(a.get("evaluation", {}).get("overall_score", 0) for a in answers) / len(answers),
        1,
    )

    if overall >= 75:
        verdict = "strong"
    elif overall >= 50:
        verdict = "moderate"
    elif overall >= 25:
        verdict = "weak"
    else:
        verdict = "very_weak"

    recommendations = []
    for topic, avg in topic_scores.items():
        if avg < 60:
            rec = domain.get_recommendation(topic, avg)
            recommendations.append({"topic": topic, "score": avg, "recommendation": rec})

    return {
        "overall_score": overall,
        "topic_scores": topic_scores,
        "verdict": verdict,
        "recommendations": recommendations,
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

    experience_level = req.experience_level or _detect_experience_level(req.resume_data)
    selected = _select_questions(domain, req.question_count, experience_level)

    session_id = str(uuid.uuid4())

    _sessions[session_id] = {
        "id": session_id,
        "domain_slug": req.domain_slug,
        "experience_level": experience_level,
        "questions": selected,
        "current_index": 0,
        "answers": [],
        "started_at": datetime.now().isoformat(),
        "finished_at": None,
        "status": "in_progress",
        "user_id": user.user_id if user else None,
        "company_id": None,
        "resume_data": req.resume_data,
        "pending_followup": None,
        "pending_evaluation": None,
    }

    first_q = selected[0] if selected else None

    return {
        "session_id": session_id,
        "domain": req.domain_slug,
        "experience_level": experience_level,
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
    session = _sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session["status"] == "completed":
        raise HTTPException(status_code=400, detail="Interview already completed")

    if session.get("pending_followup"):
        raise HTTPException(status_code=422, detail="Must answer pending follow-up first")

    answer_text = req.answer_text.strip()
    if len(answer_text) < 5:
        raise HTTPException(status_code=422, detail="Answer too short (minimum 5 characters)")

    idx = session["current_index"]
    if idx >= len(session["questions"]):
        raise HTTPException(status_code=400, detail="No more questions")

    q = session["questions"][idx]

    registry = get_registry()
    domain = registry.get(session["domain_slug"])

    eval_start = time.time()
    evaluation = _evaluate_answer(domain, q["question"], answer_text)
    eval_time = round(time.time() - eval_start, 3)

    record = {
        "question_id": q["id"],
        "question_text": q["question"],
        "topic": q["topic"],
        "difficulty": q["difficulty"],
        "answer": answer_text,
        "evaluation": evaluation,
        "timestamp": datetime.now().isoformat(),
        "timing": {
            "answer_time_seconds": req.answer_time_seconds or 0,
            "eval_time_seconds": eval_time,
        },
    }

    follow_up = evaluation.get("follow_up", "")
    if follow_up:
        session["pending_followup"] = follow_up
        session["pending_evaluation"] = evaluation
        session["pending_answer_record"] = record
        return {
            "session_id": session_id,
            "answer_recorded": True,
            "evaluation": evaluation,
            "has_next": False,
            "next_question": None,
            "follow_up": follow_up,
            "progress": f"{session['current_index'] + 1}/{len(session['questions'])}",
        }

    session["answers"].append(record)
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
        "evaluation": evaluation,
        "has_next": has_more,
        "next_question": next_q,
        "progress": f"{session['current_index']}/{len(session['questions'])}",
    }


@router.post("/{session_id}/followup")
def submit_followup(session_id: str, req: FollowupRequest):
    session = _sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if not session.get("pending_followup"):
        raise HTTPException(status_code=422, detail="No pending follow-up question")

    answer_text = req.answer_text.strip()
    if len(answer_text) < 5:
        raise HTTPException(status_code=422, detail="Answer too short (minimum 5 characters)")

    eval_start = time.time()
    followup_eval = evaluate_followup(answer_text)
    eval_time = round(time.time() - eval_start, 3)

    main_eval = session["pending_evaluation"]
    main_score = main_eval.get("overall_score", 0)
    follow_score = followup_eval.get("score", 0)
    merged_score = merge(main_score, follow_score)

    record = session["pending_answer_record"]
    record["evaluation"]["overall_score"] = merged_score
    record["evaluation"]["follow_up"] = session["pending_followup"]
    record["evaluation"]["follow_up_answer"] = answer_text
    record["evaluation"]["follow_up_score"] = followup_eval
    record["timing"]["followup_time_seconds"] = req.answer_time_seconds or 0
    record["timing"]["followup_eval_time_seconds"] = eval_time

    session["answers"].append(record)

    session["pending_followup"] = None
    session["pending_evaluation"] = None
    session["pending_answer_record"] = None

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
        "followup_evaluation": followup_eval,
        "merged_score": merged_score,
        "has_next": has_more,
        "next_question": next_q,
        "progress": f"{session['current_index']}/{len(session['questions'])}",
    }


@router.get("/{session_id}/report")
def get_report(session_id: str):
    session = _sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    registry = get_registry()
    domain = registry.get(session["domain_slug"])
    summary = _compute_session_summary(session, domain)

    per_answer = []
    for a in session["answers"]:
        per_answer.append({
            "question": a["question_text"],
            "topic": a["topic"],
            "difficulty": a["difficulty"],
            "answer": a["answer"],
            "score": a["evaluation"]["overall_score"],
            "strengths": a["evaluation"].get("strengths", []),
            "weaknesses": a["evaluation"].get("weaknesses", []),
        })

    total_answer_time = sum(
        a.get("timing", {}).get("answer_time_seconds", 0) for a in session["answers"]
    )
    total_eval_time = sum(
        a.get("timing", {}).get("eval_time_seconds", 0) for a in session["answers"]
    )

    return {
        "session_id": session_id,
        "domain": session["domain_slug"],
        "experience_level": session["experience_level"],
        "status": session["status"],
        "started_at": session["started_at"],
        "finished_at": session["finished_at"],
        "questions_total": len(session["questions"]),
        "answers_submitted": len(session["answers"]),
        "overall_score": summary["overall_score"],
        "topic_scores": summary["topic_scores"],
        "verdict": summary["verdict"],
        "recommendations": summary["recommendations"],
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
    sessions = list(_sessions.values())
    if user:
        sessions = [s for s in sessions if s.get("user_id") == user.user_id]

    return {
        "sessions": [
            {
                "id": s["id"],
                "domain": s["domain_slug"],
                "status": s["status"],
                "started_at": s["started_at"],
                "answers": len(s["answers"]),
            }
            for s in sessions
        ]
    }
