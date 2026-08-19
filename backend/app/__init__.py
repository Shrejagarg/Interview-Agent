"""Interview Agent API — FastAPI Backend"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.api import auth, domains, interviews, analytics

app = FastAPI(
    title="Interview Agent API",
    description="AI-powered interview simulator with multi-domain support",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(domains.router, prefix="/api/domains", tags=["Domains"])
app.include_router(interviews.router, prefix="/api/interviews", tags=["Interviews"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["Analytics"])


@app.get("/")
def root():
    return {"message": "Interview Agent API v2.0", "docs": "/docs"}


@app.get("/health")
def health():
    return {"status": "ok", "version": "2.0.0"}
