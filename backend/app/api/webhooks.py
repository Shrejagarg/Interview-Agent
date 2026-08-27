"""Webhook endpoints & dispatcher — ATS integrations.

Companies register HTTPS endpoints to receive async notifications when an
interview completes. Payloads are HMAC-SHA256 signed and delivery attempts are
tracked in the ``webhook_deliveries`` table.
"""

import hashlib
import hmac
import ipaddress
import json
import logging
import secrets
import socket
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.config import (
    ENV,
    WEBHOOK_TIMEOUT_SECONDS,
    WEBHOOK_MAX_RETRIES,
    WEBHOOK_ALLOW_PRIVATE,
)
from backend.app.db.database import SessionLocal, get_db
from backend.app.db.models import Webhook, WebhookDelivery
from backend.app.api.auth import require_role, UserProfile

logger = logging.getLogger(__name__)
router = APIRouter()

EVENT_INTERVIEW_COMPLETED = "interview.completed"
SUPPORTED_EVENTS = [EVENT_INTERVIEW_COMPLETED]

# ── Request / Response Models ─────────────────────────────────────────────────

class WebhookCreateRequest(BaseModel):
    url: str
    events: List[str] = [EVENT_INTERVIEW_COMPLETED]
    description: Optional[str] = None

class WebhookUpdateRequest(BaseModel):
    url: Optional[str] = None
    events: Optional[List[str]] = None
    is_active: Optional[bool] = None
    description: Optional[str] = None

class WebhookDeliveryRecord(BaseModel):
    id: str
    event_type: str
    status: str
    attempts: int
    max_retries: int
    last_attempt_at: Optional[str] = None
    response_status: Optional[int] = None
    error_message: Optional[str] = None
    created_at: str

# ── URL Validation (HTTPS + SSRF protection) ──────────────────────────────────

def _validate_webhook_url(url: str, allow_private: Optional[bool] = None) -> str:
    """Validate a webhook callback URL.

    - Must be a valid absolute URL.
    - Public hosts require HTTPS.
    - Loopback/private hosts are allowed only when ``allow_private`` is on
      (dev mode) because they make no sense on a public deployment.
    """
    if allow_private is None:
        allow_private = WEBHOOK_ALLOW_PRIVATE or ENV == "development"

    parsed = urlparse(url)
    if parsed.scheme not in ("https", "http") or not parsed.netloc:
        raise HTTPException(status_code=422, detail="Webhook URL must be a valid absolute URL (https://...)")

    host = parsed.hostname
    if not host:
        raise HTTPException(status_code=422, detail="Webhook URL missing host")

    private_resolved = False
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        infos = []
    for info in infos:
        try:
            ip = ipaddress.ip_address(info[4][0])
        except ValueError:
            continue
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            private_resolved = True
            break

    if private_resolved:
        if not allow_private:
            raise HTTPException(
                status_code=422,
                detail=f"Webhook URL resolves to a private/loopback address ({ip}) — blocked (SSRF protection)",
            )
        return url  # dev mode: http(s) to localhost / private nets is fine

    if parsed.scheme != "https":
        raise HTTPException(status_code=422, detail="Webhook URL must use HTTPS.")

    return url

# ── Serialization (never expose the signing secret) ───────────────────────────

def _serialize_webhook(wh: Webhook) -> Dict[str, Any]:
    return {
        "id": wh.id,
        "url": wh.url,
        "events": wh.events or [],
        "is_active": wh.is_active,
        "description": wh.description,
        "created_at": wh.created_at.isoformat() if wh.created_at else None,
        "updated_at": wh.updated_at.isoformat() if wh.updated_at else None,
    }

def _serialize_delivery(d: WebhookDelivery) -> WebhookDeliveryRecord:
    return WebhookDeliveryRecord(
        id=d.id,
        event_type=d.event_type,
        status=d.status,
        attempts=d.attempts,
        max_retries=d.max_retries,
        last_attempt_at=d.last_attempt_at.isoformat() if d.last_attempt_at else None,
        response_status=d.response_status,
        error_message=d.error_message,
        created_at=d.created_at.isoformat() if d.created_at else None,
    )

def _get_owned_webhook(webhook_id: str, company_id: str, db: Session) -> Webhook:
    wh = db.query(Webhook).filter(Webhook.id == webhook_id).first()
    if not wh:
        raise HTTPException(status_code=404, detail="Webhook not found")
    if wh.company_id != company_id:
        raise HTTPException(status_code=403, detail="Access denied to this webhook")
    return wh

# ── Payload Builder ───────────────────────────────────────────────────────────

def _build_payload(state: Dict[str, Any]) -> Dict[str, Any]:
    """Build the ATS-friendly webhook payload from an interview state dict."""
    answers = state.get("answers", [])
    return {
        "event": EVENT_INTERVIEW_COMPLETED,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "session": {
            "id": state.get("session_id"),
            "domain": state.get("domain"),
            "status": state.get("status", "completed"),
            "started_at": state.get("started_at"),
            "finished_at": state.get("finished_at"),
        },
        "candidate": {
            "user_id": state.get("user_id"),
        },
        "result": {
            "overall_score": state.get("_avg") or compute_avg(state),
            "verdict": state.get("verdict"),
            "topic_scores": state.get("topic_scores", {}),
            "strong_topics": state.get("strong_topics", []),
            "weak_topics": state.get("weak_topics", []),
            "questions_answered": len(answers),
            "total_questions": state.get("total_questions", 0),
        },
        "transcript": [
            {
                "question": a.get("question"),
                "answer": a.get("answer"),
                "topic": a.get("topic"),
                "difficulty": a.get("difficulty"),
                "score": a.get("evaluation", {}).get("overall_score"),
                "strengths": a.get("evaluation", {}).get("strengths", []),
                "weaknesses": a.get("evaluation", {}).get("weaknesses", []),
            }
            for a in answers
        ],
    }


def compute_avg(state: Dict[str, Any]) -> float:
    """Fallback average if the state wasn't finalized with ``_avg``."""
    answers = state.get("answers", [])
    if not answers:
        return 0.0
    scores = [a.get("evaluation", {}).get("overall_score", 0) or 0 for a in answers]
    return round(sum(scores) / len(scores), 2)

# ── Delivery ──────────────────────────────────────────────────────────────────

def _sign_payload(secret: str, body: str) -> str:
    return hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()


def _attempt_delivery(wh: Webhook, delivery: WebhookDelivery, payload: Dict[str, Any], db: Session) -> None:
    """Deliver the webhook with HMAC signing. Retries with exponential backoff."""
    body = json.dumps(payload)
    signature = _sign_payload(wh.secret, body)
    headers = {
        "Content-Type": "application/json",
        "X-Webhook-Signature": f"sha256={signature}",
        "X-Webhook-Event": delivery.event_type,
        "X-Webhook-Delivery-Id": delivery.id,
    }

    for attempt in range(1, delivery.max_retries + 1):
        try:
            resp = httpx.post(
                wh.url,
                content=body,
                headers=headers,
                timeout=WEBHOOK_TIMEOUT_SECONDS,
            )
            delivery.attempts = attempt
            delivery.last_attempt_at = datetime.utcnow()
            delivery.response_status = resp.status_code

            if 200 <= resp.status_code < 300:
                delivery.status = "delivered"
                delivery.error_message = None
                db.commit()
                return

            delivery.error_message = f"HTTP {resp.status_code}: {resp.text[:200]}"
        except Exception as e:  # network error, timeout, etc.
            delivery.attempts = attempt
            delivery.last_attempt_at = datetime.utcnow()
            delivery.error_message = f"{type(e).__name__}: {str(e)[:200]}"

        db.commit()

        if attempt < delivery.max_retries:
            time.sleep(2 ** (attempt - 1))  # backoff: 1s, 2s, 4s

    delivery.status = "failed"
    db.commit()


def dispatch_webhooks(company_id: str, state: Dict[str, Any]) -> None:
    """Background task — fire the ``interview.completed`` event for a company.

    Runs after the interview response has been returned to the client.
    Loads the company's active webhooks, builds the payload, and delivers to
    each one, recording every attempt in the ``webhook_deliveries`` table.
    """
    event_type = EVENT_INTERVIEW_COMPLETED
    payload = _build_payload(state)

    db = SessionLocal()
    try:
        webhooks = (
            db.query(Webhook)
            .filter(Webhook.company_id == company_id, Webhook.is_active.is_(True))
            .all()
        )

        for wh in webhooks:
            if not (wh.events or []) or event_type not in wh.events:
                continue

            delivery = WebhookDelivery(
                webhook_id=wh.id,
                event_type=event_type,
                payload=payload,
                status="pending",
                max_retries=WEBHOOK_MAX_RETRIES,
            )
            db.add(delivery)
            db.commit()
            db.refresh(delivery)

            try:
                _attempt_delivery(wh, delivery, payload, db)
            except Exception as e:  # never let one webhook break the loop
                logger.exception("Webhook delivery failed for webhook %s: %s", wh.id, e)
                delivery.status = "failed"
                delivery.error_message = str(e)[:200]
                db.commit()
    finally:
        db.close()


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("")
def create_webhook(
    req: WebhookCreateRequest,
    user: UserProfile = Depends(require_role("company")),
    db: Session = Depends(get_db),
):
    """Register a new webhook. Returns the HMAC secret once (unrecoverable after)."""
    if not req.events:
        raise HTTPException(status_code=422, detail="At least one event is required")
    for ev in req.events:
        if ev not in SUPPORTED_EVENTS:
            raise HTTPException(
                status_code=422,
                detail=f"Unsupported event '{ev}'. Supported: {SUPPORTED_EVENTS}",
            )

    _validate_webhook_url(req.url)

    wh = Webhook(
        company_id=user.user_id,
        url=req.url,
        events=req.events,
        secret=secrets.token_urlsafe(32),
        is_active=True,
        description=req.description,
    )
    db.add(wh)
    db.commit()
    db.refresh(wh)

    payload = _serialize_webhook(wh)
    payload["secret"] = wh.secret  # shown exactly once — do not log or return again
    return payload


@router.get("")
def list_webhooks(
    user: UserProfile = Depends(require_role("company")),
    db: Session = Depends(get_db),
):
    """List this company's webhooks (secret is never returned)."""
    webhooks = (
        db.query(Webhook)
        .filter(Webhook.company_id == user.user_id)
        .order_by(Webhook.created_at.desc())
        .all()
    )
    return {"webhooks": [_serialize_webhook(wh) for wh in webhooks]}


@router.get("/{webhook_id}")
def get_webhook(
    webhook_id: str,
    user: UserProfile = Depends(require_role("company")),
    db: Session = Depends(get_db),
):
    """Get a single webhook plus its recent delivery stats."""
    wh = _get_owned_webhook(webhook_id, user.user_id, db)

    deliveries = (
        db.query(WebhookDelivery)
        .filter(WebhookDelivery.webhook_id == wh.id)
        .order_by(WebhookDelivery.created_at.desc())
        .limit(20)
        .all()
    )

    total = db.query(WebhookDelivery).filter(WebhookDelivery.webhook_id == wh.id).count()
    delivered = (
        db.query(WebhookDelivery)
        .filter(WebhookDelivery.webhook_id == wh.id, WebhookDelivery.status == "delivered")
        .count()
    )
    failed = (
        db.query(WebhookDelivery)
        .filter(WebhookDelivery.webhook_id == wh.id, WebhookDelivery.status == "failed")
        .count()
    )

    result = _serialize_webhook(wh)
    result["deliveries"] = [d.model_dump() for d in deliveries]
    result["stats"] = {"total": total, "delivered": delivered, "failed": failed}
    return result


@router.put("/{webhook_id}")
def update_webhook(
    webhook_id: str,
    req: WebhookUpdateRequest,
    user: UserProfile = Depends(require_role("company")),
    db: Session = Depends(get_db),
):
    """Update URL, events, active flag, or description of a webhook."""
    wh = _get_owned_webhook(webhook_id, user.user_id, db)

    if req.events is not None:
        if not req.events:
            raise HTTPException(status_code=422, detail="At least one event is required")
        for ev in req.events:
            if ev not in SUPPORTED_EVENTS:
                raise HTTPException(
                    status_code=422,
                    detail=f"Unsupported event '{ev}'. Supported: {SUPPORTED_EVENTS}",
                )
        wh.events = req.events

    if req.url is not None:
        _validate_webhook_url(req.url)
        wh.url = req.url

    if req.is_active is not None:
        wh.is_active = req.is_active

    if req.description is not None:
        wh.description = req.description

    db.commit()
    db.refresh(wh)
    return _serialize_webhook(wh)


@router.delete("/{webhook_id}")
def delete_webhook(
    webhook_id: str,
    user: UserProfile = Depends(require_role("company")),
    db: Session = Depends(get_db),
):
    """Delete a webhook and its delivery history."""
    wh = _get_owned_webhook(webhook_id, user.user_id, db)
    db.query(WebhookDelivery).filter(WebhookDelivery.webhook_id == wh.id).delete()
    db.delete(wh)
    db.commit()
    return {"deleted": True, "id": webhook_id}


@router.post("/{webhook_id}/test")
def test_webhook(
    webhook_id: str,
    user: UserProfile = Depends(require_role("company")),
    db: Session = Depends(get_db),
):
    """Send a synchronous test payload to verify connectivity. Returns the result."""
    wh = _get_owned_webhook(webhook_id, user.user_id, db)

    payload = {
        "event": "test",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "message": "Test webhook from Interview Agent",
        "webhook_id": wh.id,
    }

    delivery = WebhookDelivery(
        webhook_id=wh.id,
        event_type="test",
        payload=payload,
        status="pending",
        max_retries=1,
    )
    db.add(delivery)
    db.commit()
    db.refresh(delivery)

    _attempt_delivery(wh, delivery, payload, db)
    db.refresh(delivery)
    return _serialize_delivery(delivery)


@router.get("/{webhook_id}/deliveries")
def list_deliveries(
    webhook_id: str,
    user: UserProfile = Depends(require_role("company")),
    db: Session = Depends(get_db),
):
    """View the delivery history for a webhook."""
    _get_owned_webhook(webhook_id, user.user_id, db)

    deliveries = (
        db.query(WebhookDelivery)
        .filter(WebhookDelivery.webhook_id == webhook_id)
        .order_by(WebhookDelivery.created_at.desc())
        .limit(100)
        .all()
    )
    return {"deliveries": [_serialize_delivery(d).model_dump() for d in deliveries]}