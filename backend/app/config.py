"""Centralized configuration — DB, LLM, app settings"""

import os
from dotenv import load_dotenv

load_dotenv(override=True)
# ── LLM ───────────────────────────────────────────────────────────────────────
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
MODEL_NAME = os.getenv("MODEL_NAME", "llama3")

# ── App ───────────────────────────────────────────────────────────────────────
ENV = os.getenv("ENV", "development")
CORS_ORIGINS = [
    o.strip()
    for o in os.getenv("CORS_ORIGINS", "http://localhost,http://localhost:3000").split(",")
    if o.strip()
]

# ── Auth ──────────────────────────────────────────────────────────────────────
DEFAULT_JWT_SECRET = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", DEFAULT_JWT_SECRET)
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "10080")) # 7 days

# ── Webhooks ───────────────────────────────────────────────────────────────────
WEBHOOK_TIMEOUT_SECONDS = int(os.getenv("WEBHOOK_TIMEOUT_SECONDS", "10"))
WEBHOOK_MAX_RETRIES = int(os.getenv("WEBHOOK_MAX_RETRIES", "3"))
# Localhost/private IPs are blocked for webhook URLs (SSRF protection), unless
# WEBHOOK_ALLOW_PRIVATE=1 (handy for local testing / webhook.dev)
WEBHOOK_ALLOW_PRIVATE = os.getenv("WEBHOOK_ALLOW_PRIVATE", "0") == "1"

# ── Email ───────────────────────────────────────────────────────────────────────
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
