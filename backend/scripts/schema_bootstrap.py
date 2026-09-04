"""
Schema bootstrap — run once to create all tables and seed demo data.
Works on both SQLite (dev) and Postgres (staging/Supabase) via DATABASE_URL.

Usage:
    cd <repo-root>
    python -m backend.scripts.schema_bootstrap
"""

import os
import sys
import uuid
import logging
from datetime import datetime

# Make sure the project root is on sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from backend.app.db.database import engine, Base, SessionLocal
from backend.app.db import models  # noqa: F401 — side-effect: registers all models

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_tables():
    logger.info("Creating all tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("Tables created.")


def seed_domains():
    """Insert the 5 standard domains into the raw ``domains`` table.

    Uses plain SQL so it works on both SQLite (dev) and Postgres (staging/
    Supabase), and is idempotent (skips slugs that already exist). If the
    ``domains`` table has not been created (e.g. bare SQLite dev without
    schema.sql), the insert is skipped and domain data is served by the
    in-memory registry instead.
    """
    import json
    from sqlalchemy import text
    from backend.app.db.database import engine

    domains = [
        {
            "slug": "marketing", "name": "Marketing",
            "description": "Digital marketing, branding, analytics, social media, and campaign strategy",
            "topics": ["digital_marketing", "seo", "social_media", "content_marketing", "analytics", "branding", "ppc", "email_marketing", "situational", "automation", "product_marketing", "influencer_marketing", "competitive_analysis", "conversion_optimization"],
            "scoring_dimensions": ["relevance", "clarity", "creativity", "communication"],
        },
        {
            "slug": "software_engineering", "name": "Software Engineering",
            "description": "DSA, system design, OOP, databases, APIs, and software architecture",
            "topics": ["dsa", "system_design", "oop", "databases", "api_design", "algorithms", "data_structures", "testing", "devops", "security", "performance", "code_review"],
            "scoring_dimensions": ["technical_depth", "problem_solving", "communication", "code_quality"],
        },
        {
            "slug": "finance", "name": "Finance",
            "description": "Valuation, accounting, markets, financial modeling, and analysis",
            "topics": ["accounting", "valuation", "financial_modeling", "markets", "risk_management", "corporate_finance", "investments", "taxation"],
            "scoring_dimensions": ["analytical_rigor", "technical_knowledge", "communication", "practical_application"],
        },
        {
            "slug": "hr", "name": "Human Resources",
            "description": "Recruitment, employee relations, labor law, L&D, and organizational development",
            "topics": ["recruitment", "employee_relations", "labor_law", "learning_development", "compensation_benefits", "performance_management", "diversity_inclusion", "hr_analytics"],
            "scoring_dimensions": ["empathy", "technical_knowledge", "communication", "problem_solving"],
        },
        {
            "slug": "sales", "name": "Sales",
            "description": "Pipeline management, negotiation, CRM, cold outreach, and closing",
            "topics": ["pipeline", "negotiation", "crm", "cold_outreach", "closing", "prospecting", "relationship_building", "sales_analytics"],
            "scoring_dimensions": ["persuasion", "product_knowledge", "communication", "strategic_thinking"],
        },
    ]

    try:
        with engine.begin() as conn:
            for d in domains:
                conn.execute(
                    text(
                        "INSERT INTO domains (slug, name, description, topics, scoring_dimensions, is_active) "
                        "VALUES (:slug, :name, :description, :topics, :scoring_dimensions, TRUE) "
                        "ON CONFLICT (slug) DO NOTHING"
                    ),
                    {
                        "slug": d["slug"],
                        "name": d["name"],
                        "description": d["description"],
                        "topics": json.dumps(d["topics"]),
                        "scoring_dimensions": json.dumps(d["scoring_dimensions"]),
                    },
                )
        logger.info("Seeded %d domains.", len(domains))
    except Exception as exc:  # noqa: BLE001 - table may not exist on bare SQLite dev
        logger.info("No domains table — skipping domain seed (%s).", exc)


def seed_demo_users():
    """Create demo company + candidate if they don't exist."""
    from backend.app.db.models import User
    from passlib.context import CryptContext

    pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

    demo_users = [
        {
            "id":            "demo-company-001",
            "email":         "demo@company.com",
            "password_hash": pwd_ctx.hash("Demo@1234"),
            "role":          "company",
            "full_name":     "Demo Company",
        },
        {
            "id":            "demo-candidate-001",
            "email":         "candidate@demo.com",
            "password_hash": pwd_ctx.hash("Demo@1234"),
            "role":          "candidate",
            "full_name":     "Demo Candidate",
        },
    ]

    with SessionLocal() as db:
        created = 0
        for u in demo_users:
            exists = db.query(User).filter(User.email == u["email"]).first()
            if not exists:
                db.add(User(**u, created_at=datetime.utcnow()))
                created += 1
        db.commit()

    logger.info("Demo users: %d created, %d already existed.", created, len(demo_users) - created)


def seed_sample_bank():
    """Create a sample custom question bank for the demo company."""
    from backend.app.db.models import CustomQuestionBank, CustomQuestion

    with SessionLocal() as db:
        exists = db.query(CustomQuestionBank).filter(CustomQuestionBank.company_id == "demo-company-001").first()
        if exists:
            logger.info("Sample bank already exists, skipping.")
            return

        bank = CustomQuestionBank(
            id="demo-bank-001",
            company_id="demo-company-001",
            name="Demo Marketing Bank",
            domain_slug="marketing",
            description="Sample question bank for demo purposes.",
            created_at=datetime.utcnow(),
        )
        db.add(bank)

        sample_questions = [
            ("brand_strategy", "medium", "How would you define and position a new DTC brand in a saturated market?"),
            ("social_media",   "easy",   "What metrics do you track to measure Instagram campaign success?"),
            ("analytics",      "hard",   "Walk me through a funnel analysis you performed and the decisions it drove."),
        ]
        for topic, difficulty, text in sample_questions:
            db.add(CustomQuestion(
                id=str(uuid.uuid4()),
                bank_id="demo-bank-001",
                topic=topic,
                difficulty=difficulty,
                question_text=text,
            ))

        db.commit()
        logger.info("Sample question bank seeded.")


if __name__ == "__main__":
    create_tables()
    seed_demo_users()
    seed_domains()
    seed_sample_bank()
    logger.info("Bootstrap complete.")
