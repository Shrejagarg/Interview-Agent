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
    domain = registry.get(session["domain"])

    # Engine state should be finalized before viewing details
    if session["status"] == "completed" and "_avg" not in session:
        from core.state import finalize_topics, get_average
        finalize_topics(session)
        session["_avg"] = get_average(session)

    topic_scores = session.get("topic_scores", {})
    overall = session.get("_avg", 0)
    verdict = session.get("verdict", "Unknown")

    recommendations = []
    # (Optional) Domain recommendations could go here if still wanted

    per_answer = []
    for a in session.get("answers", []):
        per_answer.append({
            "question": a.get("question"),
            "topic": a.get("topic"),
            "difficulty": a.get("evaluation", {}).get("difficulty", "?"),
            "answer": a.get("answer"),
            "score": a.get("evaluation", {}).get("overall_score", 0),
            "strengths": a.get("evaluation", {}).get("strengths", []),
            "weaknesses": a.get("evaluation", {}).get("weaknesses", []),
        })
        
    from core.state import get_integrity_score
    integrity = get_integrity_score(session)

    return {
        "session_id": session["session_id"],
        "domain": session["domain"],
        "experience_level": session.get("role_context", {}).get("experience_level", "unknown"),
        "status": session["status"],
        "user_id": session.get("user_id"),
        "started_at": session["started_at"],
        "finished_at": session.get("finished_at"),
        "questions_total": session.get("total_questions", 0),
        "answers_submitted": len(session.get("answers", [])),
        "overall_score": overall,
        "integrity_score": integrity,
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
        slug = s["domain"]
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
        sessions = [s for s in sessions if s["domain"] == domain]
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
            "id": s["session_id"],
            "domain": s["domain"],
            "experience_level": s.get("role_context", {}).get("experience_level", "unknown"),
            "status": s["status"],
            "score": session_avg,
            "started_at": s.get("started_at", ""),
            "finished_at": s.get("finished_at"),
            "answers": len(s.get("answers", [])),
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
            slug = s["domain"]
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
