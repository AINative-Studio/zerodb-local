"""
Database Configuration
SQLAlchemy database setup and session management.
Supports both PostgreSQL (full mode) and SQLite (lite mode).

Engine creation for the PostgreSQL (full-mode) branch is deferred until the
engine is first actually needed (see `_get_engine()` / `get_db()` below)
rather than happening at module-import time. SQLAlchemy's `create_engine()`
eagerly imports the DBAPI driver module (psycopg2) as soon as it's called --
not just on first connection -- so doing it at import time means merely
`import database` (e.g. from `main.py`, or from a test collecting `api/`)
unconditionally requires psycopg2-binary (a full-mode-only, `[full]` extra
dependency) to be installed, even in processes that only ever use lite mode.
Refs #50.
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator, Optional

from lite.config import is_lite_mode, get_data_path

# Base class for models
Base = declarative_base()

_engine = None
_SessionLocal: Optional[sessionmaker] = None
DATABASE_URL: Optional[str] = None


def _build_engine():
    """
    Build (but do not connect) the SQLAlchemy engine for the active backend.

    Called lazily on first use so importing this module never requires
    full-mode-only dependencies (psycopg2) unless full mode is actually used.
    """
    global DATABASE_URL

    if is_lite_mode():
        _db_path = get_data_path("zerodb.db", is_dir=False)
        DATABASE_URL = f"sqlite:///{_db_path}"
        return create_engine(
            DATABASE_URL,
            connect_args={"check_same_thread": False},
            pool_pre_ping=True,
        )

    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        "postgresql://zerodb:localpass@localhost:5432/zerodb_local"
    )
    # SQLAlchemy 2.x resolves a bare "postgresql://" scheme to the psycopg
    # (v3) driver by default, but requirements.txt installs psycopg2-binary —
    # force the psycopg2 driver explicitly so a DATABASE_URL set without the
    # dialect suffix (e.g. docker-compose.yml's zerodb-api DATABASE_URL) doesn't
    # crash the API on startup with ModuleNotFoundError: No module named 'psycopg'.
    if DATABASE_URL.startswith("postgresql://"):
        DATABASE_URL = "postgresql+psycopg2://" + DATABASE_URL[len("postgresql://"):]
    return create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20
    )


def _get_engine():
    """Return the module-level engine, building it on first access."""
    global _engine
    if _engine is None:
        _engine = _build_engine()
    return _engine


def _get_session_local() -> sessionmaker:
    """Return the module-level sessionmaker, building it on first access."""
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=_get_engine()
        )
    return _SessionLocal


def __getattr__(name: str):
    """
    PEP 562 module-level lazy attribute access.

    Preserves the historical `database.engine` / `database.SessionLocal`
    attribute access used elsewhere in the codebase, while still deferring
    actual engine construction until one of them (or get_db()) is first
    touched.
    """
    if name == "engine":
        return _get_engine()
    if name == "SessionLocal":
        return _get_session_local()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency for database sessions

    Yields:
        Session: SQLAlchemy database session
    """
    db = _get_session_local()()
    try:
        yield db
    finally:
        db.close()
