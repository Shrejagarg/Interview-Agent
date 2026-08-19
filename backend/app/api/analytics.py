"""Analytics endpoints — session comparison, recommendations, skill gaps"""

from fastapi import APIRouter, HTTPException
from typing import Optional, List

router = APIRouter()


@router.get("/sessions")
def list_analytics_sessions(domain: Optional[str] = None):
    """List sessions with analytics data."""
    return {"message": "TODO: Query from Supabase", "domain_filter": domain}


@router.get("/compare")
def compare_sessions(session_ids: str):
    """Compare multiple sessions."""
    ids = [s.strip() for s in session_ids.split(",")]
    return {"message": "TODO: Compare sessions from Supabase", "session_ids": ids}


@router.get("/recommendations/{session_id}")
def get_recommendations(session_id: str):
    """Get study recommendations for a session."""
    return {"message": "TODO: Generate recommendations from Supabase", "session_id": session_id}
