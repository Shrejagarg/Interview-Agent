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

def migrate_sqlite_missing_columns(bind=None):
    """Idempotently add columns to existing SQLite tables.

    SQLAlchemy's ``create_all`` only creates tables that don't exist yet; it
    never alters existing ones. When new columns are added to a model after the
    dev database was first created (e.g. ``invites.bank_id``), the ORM tries to
    INSERT them and fails with "table X has no column named Y". This helper
    inspects each existing table via PRAGMA and adds any missing columns from
    the mapped model, mirroring their declared types. It is a no-op on
    non-SQLite engines and on tables that are already up to date.
    """
    if bind is None:
        bind = engine
    url = str(bind.url)
    if not url.startswith("sqlite"):
        return

    types = {
        "String":  "VARCHAR",
        "Integer": "INTEGER",
        "DateTime": "DATETIME",
        "Boolean": "BOOLEAN",
        "Float":   "FLOAT",
    }

    try:
        from backend.app.db import models  # noqa: F401 - registers all models
    except Exception:  # noqa: BLE001
        logger.warning("Could not import models for migration; skipping.", exc_info=True)
        return

    with bind.begin() as conn:
        mapper_to_table = {}
        for cls in Base.registry.mappers:
            mapper_to_table.setdefault(cls.local_table.name, []).append(cls)

        for table_name, mappers in mapper_to_table.items():
            exists = conn.exec_driver_sql(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,)
            ).fetchone()
            if not exists:
                continue

            existing_cols = {
                row[1] for row in conn.exec_driver_sql(f"PRAGMA table_info({table_name})").fetchall()
            }

            added = False
            for mapper in mappers:
                for col in mapper.local_table.columns:
                    if col.name in existing_cols:
                        continue
                    col_type = types.get(type(col.type).__name__, "VARCHAR")
                    nullable = "" if col.nullable else " NOT NULL"
                    ddl = (f"ALTER TABLE {table_name} "
                           f"ADD COLUMN {col.name} {col_type}{nullable}")
                    conn.exec_driver_sql(ddl)
                    existing_cols.add(col.name)
                    added = True
                    logger.info("Migration: added column %s.%s (%s)", table_name, col.name, col_type)

            if added:
                logger.info("Migration: schema updated for table %s", table_name)

def get_db():
    """Dependency for FastAPI endpoints to get a DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
