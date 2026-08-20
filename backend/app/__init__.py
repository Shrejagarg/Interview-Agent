"""Interview Agent API — FastAPI Backend"""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.config import CORS_ORIGINS
from backend.app.api import auth, domains, interviews, analytics, company

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


@app.get("/")
def root():
    return {"message": "Interview Agent API v2.0", "docs": "/docs"}


@app.get("/health")
def health():
    from backend.app.config import is_supabase_configured
    return {
        "status": "ok",
        "version": "2.0.0",
        "supabase_configured": is_supabase_configured(),
    }
