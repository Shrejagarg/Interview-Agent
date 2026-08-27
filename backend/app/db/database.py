"""Database connection and session management."""

import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

logger = logging.getLogger(__name__)

# Fallback to local SQLite if no remote database is configured
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./interview.db")

# For SQLite, we need connect_args to allow multithreading, for Postgres we don't
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    DATABASE_URL, 
    connect_args=connect_args,
    # pool_pre_ping=True is good for prod DBs to handle disconnects
    pool_pre_ping=True if not DATABASE_URL.startswith("sqlite") else False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    """Dependency for FastAPI endpoints to get a DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
