"""Report export — shareable read-only links for completed interview reports.

A company user mints a token for one of its candidates' reports; that token can
be opened by anyone (without auth) to view the report. Tokens expire and can be
revoked by the creating company user.
"""

import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from backend.app.api.auth import UserProfile, require_role
from backend.app.db.sessions import load_session_db
from backend.app.db.result_shares import (
    create_share_db,
    get_share_db,
    get_shares_for_session_db,
    revoke_share_db,
)
from backend.app.api.company import _get_session_detail

router = APIRouter()


class ShareRequest(BaseModel):
    expires_in_days: int = 30


class RevokeResponse(BaseModel):
    revoked: bool


# ── Helpers ───────────────────────────────────────────────────────────────────

def _assert_company_owns_session(session_id: str, company_id: str) -> dict:
    session = load_session_db(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.get("company_id") != company_id:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/{session_id}/share", status_code=201)
def create_share(
    session_id: str,
    req: ShareRequest,
    user: UserProfile = Depends(require_role("company")),
):
    """Mint a shareable link for one of this company's candidate reports."""
    _assert_company_owns_session(session_id, user.user_id)
    return create_share_db(session_id, user.user_id, expires_in_days=req.expires_in_days)


@router.get("/session/{session_id}/shares")
def list_shares(
    session_id: str,
    user: UserProfile = Depends(require_role("company")),
):
    """List existing non-revoked share links for a session (company owner only)."""
    _assert_company_owns_session(session_id, user.user_id)
    shares = get_shares_for_session_db(session_id, created_by=user.user_id)
    return {"shares": [s for s in shares if not s["revoked"]]}


@router.get("/shared/{token}")
def get_shared_report(token: str):
    """Public, read-only view of a report via a valid share token."""
    share = get_share_db(token)
    if not share:
        raise HTTPException(status_code=404, detail="Share link not found or expired")
    session = _get_session_detail(share["session_id"])
    if not session:
        raise HTTPException(status_code=404, detail="Report not found")
    return {
        "report": session,
        "expires_at": share["expires_at"],
        "shared_at": share["created_at"],
    }


@router.delete("/share/{token}")
def revoke_share(
    token: str,
    user: UserProfile = Depends(require_role("company")),
):
    """Revoke a share link (only the creating company user may revoke)."""
    ok = revoke_share_db(token, user.user_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Share link not found or access denied")
    return RevokeResponse(revoked=True)
