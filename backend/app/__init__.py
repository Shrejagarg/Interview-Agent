"""Interview Agent API — FastAPI Backend"""

import logging
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.config import CORS_ORIGINS, ENV, JWT_SECRET_KEY, DEFAULT_JWT_SECRET
from backend.app.api import auth, domains, interviews, analytics, company, webhooks, campaigns, custom, reports
from backend.app.db.database import engine, Base, migrate_sqlite_missing_columns
from backend.app.db.models import (
    User, Invite, InterviewSession, Webhook, WebhookDelivery, Campaign,
    CustomQuestionBank, CustomQuestion, CreditAllotment, ResultShare,
)

logger = logging.getLogger(__name__)

# Warn if using the well-known default JWT secret
if JWT_SECRET_KEY == DEFAULT_JWT_SECRET:
    logger.warning(
        "JWT_SECRET_KEY is still the default value. Set a strong, unique "
        "secret via the JWT_SECRET_KEY environment variable before deploying."
    )
    if ENV == "production":
        raise RuntimeError(
            "Refusing to start in production with the default JWT_SECRET_KEY. "
            "Set JWT_SECRET_KEY in the environment."
        )

# Create all database tables (does nothing if they already exist)
Base.metadata.create_all(bind=engine)

# SQLite dev: add columns added to models after the DB was first created
migrate_sqlite_missing_columns()

app = FastAPI(
    title="Interview Agent API",
    description="AI-powered interview simulator with multi-domain support",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(domains.router, prefix="/api/domains", tags=["Domains"])
app.include_router(interviews.router, prefix="/api/interviews", tags=["Interviews"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["Analytics"])
app.include_router(company.router, prefix="/api/company", tags=["Company"])
app.include_router(webhooks.router, prefix="/api/webhooks", tags=["Webhooks"])
app.include_router(campaigns.router, prefix="/api/campaigns", tags=["Campaigns"])
app.include_router(custom.router,    prefix="/api/company",   tags=["Custom Banks"])
app.include_router(reports.router,   prefix="/api/reports",   tags=["Report Export"])


@app.get("/")
def root():
    return {"message": "Interview Agent API v2.0", "docs": "/docs"}


@app.get("/health")
def health():
    return {
        "status": "ok",
        "version": "2.0.0",
        "db": "sqlalchemy",
    }
