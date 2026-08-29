"""SQLAlchemy Database Models."""

import uuid
from sqlalchemy import Column, String, Integer, DateTime, Boolean, JSON, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime

from backend.app.db.database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False)  # 'candidate' or 'company'
    full_name = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Campaign(Base):
    __tablename__ = "campaigns"
    
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    company_id = Column(String, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    domain_slug = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    company = relationship("User")
    invites = relationship("Invite", back_populates="campaign", cascade="all, delete-orphan")

class Invite(Base):
    __tablename__ = "invites"
    
    token = Column(String, primary_key=True, index=True)
    company_id = Column(String, ForeignKey("users.id"), nullable=False)
    domain_slug = Column(String, nullable=False)
    question_count = Column(Integer, default=5)
    experience_level = Column(String, nullable=True)
    status = Column(String, default="active")
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Bulk campaign fields
    campaign_id = Column(String, ForeignKey("campaigns.id"), nullable=True)
    recipient_email = Column(String, nullable=True)
    recipient_name = Column(String, nullable=True)
    
    company = relationship("User")
    campaign = relationship("Campaign", back_populates="invites")

class InterviewSession(Base):
    __tablename__ = "interview_sessions"
    
    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=True)
    company_id = Column(String, ForeignKey("users.id"), nullable=True)
    domain_slug = Column(String, nullable=False)
    status = Column(String, nullable=False)
    started_at = Column(DateTime, nullable=False)
    finished_at = Column(DateTime, nullable=True)
    
    # We store the entire engine state as a JSON column to avoid breaking the core logic
    # The JSON column works differently across dialects, but SQLite supports Text and SQLAlchemy can handle it with JSON
    state_data = Column(JSON, nullable=False)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    company = relationship("User", foreign_keys=[company_id])

class Webhook(Base):
    __tablename__ = "webhooks"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    company_id = Column(String, ForeignKey("users.id"), nullable=False)
    url = Column(String, nullable=False)
    events = Column(JSON, default=["interview.completed"])  # which events trigger this webhook
    secret = Column(String, nullable=False)                 # HMAC-SHA256 signing secret
    is_active = Column(Boolean, default=True)
    description = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    company = relationship("User")


class WebhookDelivery(Base):
    __tablename__ = "webhook_deliveries"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    webhook_id = Column(String, ForeignKey("webhooks.id"), nullable=False)
    event_type = Column(String, nullable=False)
    payload = Column(JSON, nullable=False)
    status = Column(String, default="pending")   # pending / delivered / failed
    attempts = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    last_attempt_at = Column(DateTime, nullable=True)
    response_status = Column(Integer, nullable=True)  # HTTP status code from receiver
    error_message = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    webhook = relationship("Webhook")
