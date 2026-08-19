"""Analytics endpoints — session comparison, recommendations, skill gaps"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.app.domains import get_registry
from backend.app.api.interviews import _sessions, _compute_session_summary

logger = logging.getLogger(__name__)
router = APIRouter()


class SessionSummary(BaseModel):
    session_id: str
    domain: str
    overall_score: float
    topic_scores: dict
    verdict: str
    questions_total: int
    answers_submitted: int
    started_at: str
    finished_at: Optional[str] = None


@router.get("/sessions")
def list_analytics_sessions(domain: Optional[str] = None):
    """List all sessions with analytics summaries."""
    results = []
    for sid, s in _sessions.items():
        if domain and s["domain_slug"] != domain:
            continue
        registry = get_registry()
        d = registry.get(s["domain_slug"])
        summary = _compute_session_summary(s, d)
        results.append({
            "session_id": sid,
            "domain": s["domain_slug"],
            "status": s["status"],
            "overall_score": summary["overall_score"],
            "topic_scores": summary["topic_scores"],
            "verdict": summary["verdict"],
            "questions_total": len(s["questions"]),
            "answers_submitted": len(s["answers"]),
            "started_at": s["started_at"],
            "finished_at": s.get("finished_at"),
        })
    return {"sessions": results, "total": len(results)}


@router.get("/compare")
def compare_sessions(session_ids: str):
    """Compare two or more sessions side-by-side."""
    ids = [s.strip() for s in session_ids.split(",") if s.strip()]
    if len(ids) < 2:
        raise HTTPException(status_code=422, detail="Provide at least 2 comma-separated session IDs")

    registry = get_registry()
    summaries = []
    for sid in ids:
        s = _sessions.get(sid)
        if not s:
            raise HTTPException(status_code=404, detail=f"Session '{sid}' not found")
        d = registry.get(s["domain_slug"])
        summary = _compute_session_summary(s, d)
        summaries.append({
            "session_id": sid,
            "domain": s["domain_slug"],
            "overall_score": summary["overall_score"],
            "topic_scores": summary["topic_scores"],
            "verdict": summary["verdict"],
        })

    sorted_by_score = sorted(summaries, key=lambda x: x["overall_score"], reverse=True)
    rankings = [
        {"rank": i + 1, "session_id": s["session_id"], "score": s["overall_score"]}
        for i, s in enumerate(sorted_by_score)
    ]

    all_topics: dict = {}
    for s in summaries:
        for topic, score in s["topic_scores"].items():
            all_topics.setdefault(topic, []).append(score)

    topic_averages = {
        topic: round(sum(scores) / len(scores), 1)
        for topic, scores in all_topics.items()
    }

    return {
        "sessions": summaries,
        "rankings": rankings,
        "topic_averages": topic_averages,
    }


@router.get("/recommendations/{session_id}")
def get_recommendations(session_id: str):
    """Get personalized study recommendations for a session."""
    session = _sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")

    registry = get_registry()
    domain = registry.get(session["domain_slug"])
    summary = _compute_session_summary(session, domain)

    return {
        "session_id": session_id,
        "domain": session["domain_slug"],
        "overall_score": summary["overall_score"],
        "verdict": summary["verdict"],
        "topic_scores": summary["topic_scores"],
        "recommendations": summary["recommendations"],
    }
