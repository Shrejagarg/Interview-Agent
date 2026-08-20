"""Interview endpoints — start, answer, and complete interviews with LLM evaluation"""

import json
import random
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from backend.app.domains import get_registry
from backend.app.domains.base import BaseDomain
from backend.app.config import OLLAMA_HOST, MODEL_NAME
from backend.app.api.auth import get_optional_user, UserProfile

logger = logging.getLogger(__name__)
router = APIRouter()

# In-memory session store (will be replaced with Supabase)
_sessions: Dict[str, Dict[str, Any]] = {}


# ── Request / Response Models ─────────────────────────────────────────────────

class StartInterviewRequest(BaseModel):
    domain_slug: str
    question_count: int = 5
    experience_level: Optional[str] = None  # fresher | mid | senior
    resume_data: Optional[Dict[str, Any]] = None


class AnswerRequest(BaseModel):
    question_id: str
    answer_text: str


# ── Helpers ───────────────────────────────────────────────────────────────────

def _detect_experience_level(resume_data: Optional[Dict[str, Any]]) -> str:
    """Infer experience level from resume data."""
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
    """Select questions using difficulty distribution and topic coverage."""
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


def _call_llm(prompt: str) -> Optional[str]:
    """Send a prompt to Ollama and return the raw text response."""
    try:
        import ollama
        response = ollama.chat(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
        )
        return response["message"]["content"]
    except Exception as e:
        logger.warning("LLM call failed: %s", e)
        return None


def _parse_llm_json(raw: str) -> Optional[Dict[str, Any]]:
    """Extract a JSON object from LLM output (handles code fences, etc.)."""
    if not raw:
        return None
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        idx_start = text.find("{")
        idx_end = text.rfind("}")
        if idx_start != -1 and idx_end > idx_start:
            try:
                return json.loads(text[idx_start : idx_end + 1])
            except json.JSONDecodeError:
                pass
    return None


def _evaluate_answer(
    domain: BaseDomain,
    question_text: str,
    answer_text: str,
) -> Dict[str, Any]:
    """Evaluate an answer using the LLM. Returns a dict with scores."""
    prompt = domain.get_evaluation_prompt(question_text, answer_text)
    raw = _call_llm(prompt)
    parsed = _parse_llm_json(raw)

    if not parsed or not isinstance(parsed, dict):
        logger.warning("LLM returned unparseable evaluation, using fallback scores")
        return _fallback_evaluation(answer_text)

    defaults = {
        dim: 50 for dim in domain.scoring_dimensions
    }
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

    defaults["overall_score"] = max(0, min(100, int(defaults["overall_score"])))

    return defaults


def _fallback_evaluation(answer_text: str) -> Dict[str, Any]:
    """Score when the LLM is unavailable — basic heuristic."""
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
    """Build the full report from accumulated answer evaluations."""
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
    """Start a new interview session."""
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
    """Submit an answer — LLM evaluation runs automatically."""
    session = _sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session["status"] == "completed":
        raise HTTPException(status_code=400, detail="Interview already completed")

    answer_text = req.answer_text.strip()
    if len(answer_text) < 5:
        raise HTTPException(status_code=422, detail="Answer too short (minimum 5 characters)")

    idx = session["current_index"]
    if idx >= len(session["questions"]):
        raise HTTPException(status_code=400, detail="No more questions")

    q = session["questions"][idx]

    registry = get_registry()
    domain = registry.get(session["domain_slug"])

    evaluation = _evaluate_answer(domain, q["question"], answer_text)

    record = {
        "question_id": q["id"],
        "question_text": q["question"],
        "topic": q["topic"],
        "difficulty": q["difficulty"],
        "answer": answer_text,
        "evaluation": evaluation,
        "timestamp": datetime.now().isoformat(),
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


@router.get("/{session_id}/report")
def get_report(session_id: str):
    """Get the full interview report with scores and recommendations."""
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
    }


@router.get("")
def list_sessions(user: Optional[UserProfile] = Depends(get_optional_user)):
    """List sessions — filters by user_id if authenticated."""
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
