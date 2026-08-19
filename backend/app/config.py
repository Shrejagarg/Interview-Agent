"""Supabase client configuration"""

import os
from functools import lru_cache
from typing import Optional

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")


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


def is_configured() -> bool:
    """Check if Supabase is configured."""
    return bool(SUPABASE_URL and SUPABASE_ANON_KEY)
