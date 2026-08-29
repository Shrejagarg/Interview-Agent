"""Quarantine guard — backend tests must never reach the development database.

Historically ``conftest.py`` ran a ``DELETE`` loop against the engine, i.e. the
real ``backend/interview.db``, on every test session. The DATABASE_URL override
in conftest now points the engine at a throwaway temp file; these tests pin
that behaviour so a refactor can't silently regress it.
"""

import os
from sqlalchemy import inspect
from backend.app.db.database import DATABASE_URL, engine


def _sqlite_path() -> str:
    """The filesystem path the engine is actually bound to ('' if not sqlite)."""
    return (engine.url.database or "").replace("/", os.sep)


def test_engine_is_bound_to_the_temp_test_db():
    path = _sqlite_path()
    assert path, "expected a sqlite engine for tests"
    name = os.path.basename(path)
    assert name.startswith("interview_test_"), (
        f"engine bound to unexpected path {path!r}; the DATABASE_URL override in "
        "conftest.py should redirect tests to a temp db"
    )
    assert name != "interview.db"


def test_dev_db_files_are_not_the_engine_target():
    path = _sqlite_path()
    assert os.path.abspath(path).lower() != os.path.abspath("interview.db").lower()
    assert os.path.abspath(path).lower() != os.path.abspath(
        os.path.join("backend", "interview.db")
    ).lower()


def test_temp_db_schema_was_created_on_import():
    # backend/app/__init__.py runs create_all against the (temp) engine.
    insp = inspect(engine)
    for table in ("users", "invites", "interview_sessions", "campaigns"):
        assert insp.has_table(table), f"expected temp DB to have table {table!r}"