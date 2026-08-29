"""Idempotent dev seed.

Restores demo accounts (and optionally demo campaign/invite rows) into the
configured database WITHOUT touching app code, schema, or infrastructure.

Usage (from repo root):
    venv\\Scripts\\python -m backend.scripts.seed_dev
    venv\\Scripts\\python -m backend.scripts.seed_dev --with-sample-data

The script refuses to run when the app targets production (ENV=production).
Re-running is safe: accounts are upserted by email, and sample rows are only
created when they do not already exist.
"""

import argparse
import logging
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("seed_dev")

from sqlalchemy import text  # noqa: E402
from backend.app.api.auth import _hash_password  # noqa: E402
from backend.app.config import ENV  # noqa: E402
from backend.app.db.database import DATABASE_URL, engine, SessionLocal  # noqa: E402
from backend.app.db.models import User, Campaign, Invite  # noqa: E402

PASSWORD = "Passw0rd123!"

ACCOUNTS = [
    {
        "email": "company@test.io",
        "role": "company",
        "full_name": "Demo Company",
    },
    {
        "email": "candidate@test.io",
        "role": "candidate",
        "full_name": "Demo Candidate",
    },
]

SAMPLE_DATA = {
    "campaign": {
        "name": "Software Engineering Q3",
        "domain_slug": "software_engineering",
    },
    "invites": [
        {"domain_slug": "software_engineering", "question_count": 5},
        {"domain_slug": "marketing", "question_count": 5},
    ],
}


def _upsert_accounts(session):
    created = 0
    updated = 0
    skipped = 0
    for account in ACCOUNTS:
        existing = session.query(User).filter(User.email == account["email"]).first()
        if existing:
            if existing.role == account["role"]:
                skipped += 1
                logger.info("  = %s (already present)", account["email"])
                continue
            existing.role = account["role"]
            existing.full_name = account["full_name"]
            updated += 1
            logger.info("  ~ %s (role updated -> %s)", account["email"], account["role"])
            continue

        user = User(
            id=str(uuid.uuid4()),
            email=account["email"],
            password_hash=_hash_password(PASSWORD),
            role=account["role"],
            full_name=account["full_name"],
        )
        session.add(user)
        created += 1
        logger.info("  + %s (password '%s')", account["email"], PASSWORD)

    session.commit()
    return created, updated, skipped


def _seed_sample_data(session, company):
    created = 0
    campaign_name = SAMPLE_DATA["campaign"]["name"]
    campaign = (
        session.query(Campaign)
        .filter(Campaign.company_id == company.id, Campaign.name == campaign_name)
        .first()
    )
    if not campaign:
        campaign = Campaign(company_id=company.id, name=campaign_name, domain_slug=SAMPLE_DATA["campaign"]["domain_slug"])
        session.add(campaign)
        session.flush()
        created += 1
        logger.info("  + campaign '%s'", campaign_name)

    existing_tokens = {row.token for row in session.query(Invite).filter(Invite.company_id == company.id)}
    for invite in SAMPLE_DATA["invites"]:
        if invite["domain_slug"] in existing_tokens:
            continue
        token = str(os.urandom(16).hex())
        session.add(
            Invite(
                token=token,
                company_id=company.id,
                domain_slug=invite["domain_slug"],
                question_count=invite["question_count"],
                campaign_id=campaign.id,
                status="active",
            )
        )
        existing_tokens.add(invite["domain_slug"])
        created += 1
        logger.info("  + invite for '%s' (%d questions)", invite["domain_slug"], invite["question_count"])

    session.commit()
    return created


def _sync_schema_columns(session):
    """Additively bring SQLite tables in line with the models (never drops or alters existing data)."""
    if not str(DATABASE_URL).startswith("sqlite"):
        return
    tables = {
        "invites": [
            ("campaign_id", "VARCHAR"),
            ("recipient_email", "VARCHAR"),
            ("recipient_name", "VARCHAR"),
        ],
    }
    changed = 0
    for table, columns in tables.items():
        present = {row[1] for row in session.execute(text(f"PRAGMA table_info({table})"))}
        for column_name, column_type in columns:
            if column_name not in present:
                session.execute(text(f"ALTER TABLE {table} ADD COLUMN {column_name} {column_type}"))
                logger.info("  ~ schema: added %s.%s", table, column_name)
                changed += 1
    if changed:
        session.commit()


def main():
    if ENV == "production":
        logger.error("Refusing to seed: ENV=production. Set ENV to development to run the dev seed.")
        return 1

    parser = argparse.ArgumentParser(description="Seed demo data into the app database")
    parser.add_argument("--with-sample-data", action="store_true", help="Also create a demo campaign + invites")
    args = parser.parse_args()

    logger.info("Target DB: %s", DATABASE_URL)
    logger.info("Creating tables if needed...")
    from backend.app.db.database import Base
    import backend.app.db.models as models  # noqa: F401

    Base.metadata.create_all(bind=engine)

    session = SessionLocal()
    try:
        _sync_schema_columns(session)
        created, updated, skipped = _upsert_accounts(session)
        logger.info("Accounts: %d created, %d updated, %d skipped", created, updated, skipped)

        company = session.query(User).filter(User.email == "company@test.io").first()
        if args.with_sample_data and company:
            sample_created = _seed_sample_data(session, company)
            logger.info("Sample data: %d rows created", sample_created)
        else:
            logger.info("Sample data: skipped (use --with-sample-data)")
    finally:
        session.close()

    logger.info("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())