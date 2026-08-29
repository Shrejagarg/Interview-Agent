"""Tests for the real db/domains.py SQLAlchemy helpers.

The conftest autouse fixture monkeypatches these helpers with mock data for the
API tests, so we capture the ORIGINAL function objects at import time (before
any fixture runs) and drive them against the throwaway temp DB with real rows.
The domains/questions/skills/job_titles tables are created on the temp engine
only (they are not SQLAlchemy models, so `create_all` skips them).
"""

import json
import uuid

from sqlalchemy import text

from backend.app.db.database import engine, SessionLocal
import backend.app.db.domains as db_domains_mod

# Capture the real functions before the conftest autouse fixture swaps the
# module attributes for mocks — this module is imported at collection time,
# which always precedes any fixture setup.
_real_list_domains = db_domains_mod.list_domains_db
_real_get_domain = db_domains_mod.get_domain_db
_real_get_questions = db_domains_mod.get_domain_questions_db
_real_get_skills = db_domains_mod.get_domain_skills_db
_real_get_titles = db_domains_mod.get_domain_job_titles_db


_DID = str(uuid.uuid4())

_CREATE_SQL = """
CREATE TABLE IF NOT EXISTS domains (
    id TEXT PRIMARY KEY, slug TEXT, name TEXT, description TEXT,
    topics TEXT, scoring_dimensions TEXT, is_active INTEGER
);
CREATE TABLE IF NOT EXISTS questions (
    id TEXT PRIMARY KEY, domain_id TEXT, domain_slug TEXT, external_id TEXT,
    topic TEXT, difficulty TEXT, roles TEXT, question_text TEXT, is_active INTEGER
);
CREATE TABLE IF NOT EXISTS skills (
    id TEXT PRIMARY KEY, domain_id TEXT, domain_slug TEXT, category TEXT, skill_name TEXT
);
CREATE TABLE IF NOT EXISTS job_titles (
    id TEXT PRIMARY KEY, domain_id TEXT, level TEXT, title TEXT
);
"""

with engine.begin() as conn:
    for stmt in _CREATE_SQL.split(";"):
        if stmt.strip():
            conn.execute(text(stmt.strip()))
    conn.execute(text(
        "INSERT OR IGNORE INTO domains (id, slug, name, description, topics, scoring_dimensions, is_active)"
        " VALUES (:id, 'marketing', 'Marketing', 'desc', :topics, :dims, 1)"
    ), {"id": _DID, "topics": json.dumps(["seo", "ppc"]), "dims": json.dumps(["relevance"])})
    conn.execute(text(
        "INSERT OR IGNORE INTO questions (id, domain_id, domain_slug, external_id, topic, difficulty, roles, question_text, is_active)"
        " VALUES (:id, :did, 'marketing', 'mkt_01', 'seo', 'easy', :roles, 'What is SEO?', 1)"
    ), {"id": str(uuid.uuid4()), "did": _DID, "roles": json.dumps(["fresher", "mid"])})
    conn.execute(text(
        "INSERT OR IGNORE INTO skills (id, domain_id, domain_slug, category, skill_name)"
        " VALUES (:id, :did, 'marketing', 'seo', 'google analytics')"
    ), {"id": str(uuid.uuid4()), "did": _DID})
    conn.execute(text(
        "INSERT OR IGNORE INTO job_titles (id, domain_id, level, title)"
        " VALUES (:id, :did, 'mid', 'marketing manager')"
    ), {"id": str(uuid.uuid4()), "did": _DID})


class TestDomainDbReal:
    def test_list_domains(self):
        domains = _real_list_domains()
        assert any(d["slug"] == "marketing" for d in domains)
        marketing = next(d for d in domains if d["slug"] == "marketing")
        assert marketing["topics"] == ["seo", "ppc"]
        assert marketing["scoring_dimensions"] == ["relevance"]
        assert marketing["description"] == "desc"

    def test_get_domain(self):
        d = _real_get_domain("marketing")
        assert d is not None
        assert d["topics"] == ["seo", "ppc"]

    def test_get_domain_missing_returns_none(self):
        assert _real_get_domain("does-not-exist") is None

    def test_get_domain_questions(self):
        rows = _real_get_questions(_DID)
        assert len(rows) == 1
        q = rows[0]
        assert q["external_id"] == "mkt_01"
        assert q["roles"] == ["fresher", "mid"]
        assert q["question_text"] == "What is SEO?"
        assert q["is_active"] == 1

    def test_get_domain_skills(self):
        rows = _real_get_skills(_DID)
        assert len(rows) == 1
        assert rows[0]["skill_name"] == "google analytics"

    def test_get_domain_job_titles(self):
        rows = _real_get_titles(_DID)
        assert len(rows) == 1
        assert rows[0]["title"] == "marketing manager"

    def test_helpers_return_empty_for_unknown_domain(self):
        assert _real_list_domains() is not None
        assert _real_get_questions("00000000-0000-0000-0000-000000000999") == []
        assert _real_get_skills("00000000-0000-0000-0000-000000000999") == []
        assert _real_get_titles("00000000-0000-0000-0000-000000000999") == []