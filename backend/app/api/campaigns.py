import csv
import logging
import secrets
from datetime import datetime
from io import StringIO
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from backend.app.db.database import get_db
from backend.app.db.models import Campaign, Invite
from backend.app.api.auth import require_role, UserProfile
from backend.app.services.email import send_bulk_invites

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/upload")
async def upload_campaign(
    name: str = Form(...),
    domain_slug: str = Form(...),
    file: UploadFile = File(...),
    user: UserProfile = Depends(require_role("company")),
    db: Session = Depends(get_db),
):
    """
    Parse a CSV file (Name, Email), create a Campaign, generate Invites, and dispatch mock emails.
    """
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed")

    content = await file.read()
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="CSV file must be UTF-8 encoded")

    csv_reader = csv.DictReader(StringIO(text))
    # normalize headers
    headers = [h.strip().lower() for h in (csv_reader.fieldnames or [])]
    if "email" not in headers:
        raise HTTPException(status_code=400, detail="CSV must contain an 'email' column")
    
    csv_reader.fieldnames = headers

    # Create campaign
    campaign = Campaign(
        company_id=user.user_id,
        name=name,
        domain_slug=domain_slug
    )
    db.add(campaign)
    db.commit()
    db.refresh(campaign)

    email_payloads = []
    
    for row in csv_reader:
        email = row.get("email", "").strip()
        if not email:
            continue
            
        recipient_name = row.get("name", "").strip()

        token = secrets.token_urlsafe(32)
        invite = Invite(
            token=token,
            company_id=user.user_id,
            domain_slug=domain_slug,
            campaign_id=campaign.id,
            recipient_email=email,
            recipient_name=recipient_name,
            question_count=5
        )
        db.add(invite)
        
        # Build mock email payload
        # In a real app, the base URL would come from config
        invite_link = f"http://localhost:3000/join?token={token}"
        email_payloads.append({
            "name": recipient_name,
            "email": email,
            "link": invite_link
        })

    db.commit()

    # Dispatch emails asynchronously in a real app, here we mock it synchronously for simplicity
    send_bulk_invites(campaign.name, email_payloads)

    return {
        "id": campaign.id,
        "name": campaign.name,
        "domain_slug": campaign.domain_slug,
        "created_at": campaign.created_at.isoformat(),
        "total_invites": len(email_payloads),
        "status": "completed",
        "message": "Campaign launched successfully"
    }


@router.get("")
def list_campaigns(
    user: UserProfile = Depends(require_role("company")),
    db: Session = Depends(get_db)
):
    campaigns = db.query(Campaign).filter(Campaign.company_id == user.user_id).order_by(Campaign.created_at.desc()).all()
    
    return {
        "campaigns": [
            {
                "id": c.id,
                "name": c.name,
                "domain_slug": c.domain_slug,
                "created_at": c.created_at.isoformat(),
                "total_invites": len(c.invites),
                "status": "completed"
            }
            for c in campaigns
        ]
    }


@router.get("/{campaign_id}")
def get_campaign(
    campaign_id: str,
    user: UserProfile = Depends(require_role("company")),
    db: Session = Depends(get_db)
):
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id, Campaign.company_id == user.user_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
        
    return {
        "id": campaign.id,
        "name": campaign.name,
        "domain_slug": campaign.domain_slug,
        "created_at": campaign.created_at.isoformat(),
        "invites": [
            {
                "token": inv.token,
                "recipient_name": inv.recipient_name,
                "recipient_email": inv.recipient_email,
                "status": inv.status,
                "created_at": inv.created_at.isoformat()
            }
            for inv in campaign.invites
        ]
    }
