"""Supabase client initialization — wraps backend.app.config with graceful fallback"""

import logging
from backend.app.config import get_supabase, is_supabase_configured

logger = logging.getLogger(__name__)

_client = None
_configured = None


def get_db():
    """Get the Supabase client. Returns None if not configured.

    Tests can override this by patching ``backend.app.db.supabase.get_db``.
    """
    global _client, _configured
    if _configured is None:
        _configured = is_supabase_configured()
        if not _configured:
            logger.warning("Supabase not configured — DB operations will raise at call time")
    if _client is None and _configured:
        _client = get_supabase()
    return _client


def get_db_or_raise():
    """Get the Supabase client, raising if unavailable."""
    db = get_db()
    if db is None:
        raise RuntimeError(
            "Supabase is not configured. "
            "Set SUPABASE_URL and SUPABASE_ANON_KEY environment variables."
        )
    return db


def reset_client():
    """Reset cached client (for testing)."""
    global _client, _configured
    _client = None
    _configured = None
