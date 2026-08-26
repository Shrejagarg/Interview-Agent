"""Centralized configuration — Supabase, LLM, app settings"""

import os
from functools import lru_cache
from typing import Optional

# ── Supabase ──────────────────────────────────────────────────────────────────
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

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


@lru_cache()
def get_supabase():
    """Get a Supabase client (cached). Returns None if not configured."""
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        return None
    from supabase import create_client
    return create_client(SUPABASE_URL, SUPABASE_ANON_KEY)


@lru_cache()
def get_supabase_admin():
    """Get a Supabase admin client with service role key."""
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        return None
    from supabase import create_client
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)


def is_supabase_configured() -> bool:
    """Check if Supabase is configured."""
    return bool(SUPABASE_URL and SUPABASE_ANON_KEY)
