"""Company endpoints — dashboard, sessions, candidates, comparison, and invites"""

import logging
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from backend.app.domains import get_registry
from backend.app.api.auth import get_current_user, UserProfile, require_role
from backend.app.api.interviews import _sessions

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Request / Response Models ─────────────────────────────────────────────────

class InviteRequest(BaseModel):
    email: str
    domain_slug: str
    question_count: int = 5
    experience_level: Optional[str] = None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_company_sessions(company_id: str) -> List[Dict[str, Any]]:
    """Return all sessions linked to a company."""
    return [s for s in _sessions.values() if s.get("company_id") == company_id]


def _get_session_detail(session_id: str) -> Dict[str, Any]:
    """Return full session detail with scores."""
    session = _sessions.get(session_id)
    if not session:
        return None

    registry = get_registry()
    domain = registry.get(session["domain_slug"])

    topic_buckets: Dict[str, List[int]] = {}
    for a in session["answers"]:
        topic = a.get("topic", "unknown")
        score = a.get("evaluation", {}).get("overall_score", 0)
        topic_buckets.setdefault(topic, []).append(score)

    topic_scores = {}
    for topic, scores in topic_buckets.items():
        topic_scores[topic] = round(sum(scores) / len(scores), 1)

    overall = 0
    if session["answers"]:
        overall = round(
            sum(a.get("evaluation", {}).get("overall_score", 0) for a in session["answers"])
            / len(session["answers"]),
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
    if domain:
        for topic, avg in topic_scores.items():
            if avg < 60:
                rec = domain.get_recommendation(topic, avg)
                recommendations.append({"topic": topic, "score": avg, "recommendation": rec})

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
        "session_id": session["id"],
        "domain": session["domain_slug"],
        "experience_level": session["experience_level"],
        "status": session["status"],
        "user_id": session.get("user_id"),
        "started_at": session["started_at"],
        "finished_at": session.get("finished_at"),
        "questions_total": len(session["questions"]),
        "answers_submitted": len(session["answers"]),
        "overall_score": overall,
        "topic_scores": topic_scores,
        "verdict": verdict,
        "recommendations": recommendations,
        "answers": per_answer,
    }


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/dashboard")
def get_dashboard(user: UserProfile = Depends(require_role("company"))):
    """Company dashboard with aggregate stats."""
    sessions = _get_company_sessions(user.user_id)

    total_sessions = len(sessions)
    completed = [s for s in sessions if s["status"] == "completed"]

    unique_candidates = set()
    for s in sessions:
        uid = s.get("user_id")
        if uid:
            unique_candidates.add(uid)

    avg_score = 0.0
    if completed:
        scores = []
        for s in completed:
            if s["answers"]:
                session_avg = sum(a["evaluation"]["overall_score"] for a in s["answers"]) / len(s["answers"])
                scores.append(session_avg)
        if scores:
            avg_score = round(sum(scores) / len(scores), 1)

    domain_breakdown: Dict[str, int] = {}
    for s in sessions:
        slug = s["domain_slug"]
        domain_breakdown[slug] = domain_breakdown.get(slug, 0) + 1

    return {
        "total_sessions": total_sessions,
        "unique_candidates": len(unique_candidates),
        "avg_score": avg_score,
        "domain_breakdown": domain_breakdown,
    }


@router.get("/sessions")
def list_company_sessions(
    domain: Optional[str] = None,
    status: Optional[str] = None,
    user: UserProfile = Depends(require_role("company")),
):
    """List sessions for this company with optional filters."""
    sessions = _get_company_sessions(user.user_id)

    if domain:
        sessions = [s for s in sessions if s["domain_slug"] == domain]
    if status:
        sessions = [s for s in sessions if s["status"] == status]

    result = []
    for s in sessions:
        session_avg = 0.0
        if s["answers"]:
            session_avg = round(
                sum(a["evaluation"]["overall_score"] for a in s["answers"]) / len(s["answers"]),
                1,
            )
        result.append({
            "id": s["id"],
            "domain": s["domain_slug"],
            "experience_level": s["experience_level"],
            "status": s["status"],
            "score": session_avg,
            "started_at": s["started_at"],
            "finished_at": s.get("finished_at"),
            "answers": len(s["answers"]),
            "user_id": s.get("user_id"),
        })

    return {"sessions": result}


@router.get("/sessions/{session_id}")
def get_company_session(
    session_id: str,
    user: UserProfile = Depends(require_role("company")),
):
    """Get full session detail for a company."""
    session = _sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.get("company_id") != user.user_id:
        raise HTTPException(status_code=403, detail="Access denied to this session")

    detail = _get_session_detail(session_id)
    return detail


@router.get("/candidates")
def list_candidates(user: UserProfile = Depends(require_role("company"))):
    """List unique candidates with their best scores per domain."""
    sessions = _get_company_sessions(user.user_id)

    candidates: Dict[str, Dict[str, Any]] = {}
    for s in sessions:
        uid = s.get("user_id")
        if not uid:
            continue

        if uid not in candidates:
            candidates[uid] = {
                "user_id": uid,
                "total_sessions": 0,
                "domain_scores": {},
            }

        candidates[uid]["total_sessions"] += 1

        if s["answers"]:
            session_avg = round(
                sum(a["evaluation"]["overall_score"] for a in s["answers"]) / len(s["answers"]),
                1,
            )
            slug = s["domain_slug"]
            current_best = candidates[uid]["domain_scores"].get(slug, 0)
            if session_avg > current_best:
                candidates[uid]["domain_scores"][slug] = session_avg

    result = []
    for c in candidates.values():
        all_scores = list(c["domain_scores"].values())
        c["avg_score"] = round(sum(all_scores) / len(all_scores), 1) if all_scores else 0.0
        result.append(c)

    result.sort(key=lambda x: x["avg_score"], reverse=True)
    return {"candidates": result}


@router.get("/compare")
def compare_sessions(
    session_ids: str,
    user: UserProfile = Depends(require_role("company")),
):
    """Compare multiple sessions side-by-side. session_ids is a comma-separated list."""
    ids = [sid.strip() for sid in session_ids.split(",") if sid.strip()]
    if len(ids) < 2:
        raise HTTPException(status_code=422, detail="Provide at least 2 session IDs to compare")

    comparisons = []
    for sid in ids:
        session = _sessions.get(sid)
        if not session:
            raise HTTPException(status_code=404, detail=f"Session {sid} not found")
        if session.get("company_id") != user.user_id:
            raise HTTPException(status_code=403, detail=f"Access denied to session {sid}")

        detail = _get_session_detail(sid)
        comparisons.append(detail)

    # Compute ranking
    comparisons.sort(key=lambda x: x["overall_score"], reverse=True)
    for i, c in enumerate(comparisons):
        c["rank"] = i + 1

    return {"comparisons": comparisons}


@router.post("/invite")
def invite_candidate(
    req: InviteRequest,
    user: UserProfile = Depends(require_role("company")),
):
    """Create an interview invitation for a candidate."""
    registry = get_registry()
    domain = registry.get(req.domain_slug)
    if not domain:
        raise HTTPException(status_code=404, detail=f"Domain '{req.domain_slug}' not found")

    token = str(uuid.uuid4())

    return {
        "invite_token": token,
        "email": req.email,
        "domain": req.domain_slug,
        "question_count": req.question_count,
        "created_at": datetime.now().isoformat(),
        "created_by": user.user_id,
    }
