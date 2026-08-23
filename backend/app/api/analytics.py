"""Analytics endpoints — session comparison, recommendations, skill gaps"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.app.domains import get_registry
from backend.app.api.interviews import _sessions

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
        if domain and s["domain"] != domain:
            continue
            
        if s["status"] == "completed" and "_avg" not in s:
            from core.state import finalize_topics, get_average
            finalize_topics(s)
            s["_avg"] = get_average(s)

        results.append({
            "session_id": sid,
            "domain": s["domain"],
            "status": s["status"],
            "overall_score": s.get("_avg", 0),
            "topic_scores": s.get("topic_scores", {}),
            "verdict": s.get("verdict", "Unknown"),
            "questions_total": s.get("total_questions", 0),
            "answers_submitted": len(s.get("answers", [])),
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
        if s["status"] == "completed" and "_avg" not in s:
            from core.state import finalize_topics, get_average
            finalize_topics(s)
            s["_avg"] = get_average(s)

        summaries.append({
            "session_id": sid,
            "domain": s["domain"],
            "overall_score": s.get("_avg", 0),
            "topic_scores": s.get("topic_scores", {}),
            "verdict": s.get("verdict", "Unknown"),
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
    domain = registry.get(session["domain"])
    if session["status"] == "completed" and "_avg" not in session:
        from core.state import finalize_topics, get_average
        finalize_topics(session)
        session["_avg"] = get_average(session)

    return {
        "session_id": session_id,
        "domain": session["domain"],
        "overall_score": session.get("_avg", 0),
        "verdict": session.get("verdict", "Unknown"),
        "topic_scores": session.get("topic_scores", {}),
        "recommendations": [], # Defer recommendations to core logic later
    }
