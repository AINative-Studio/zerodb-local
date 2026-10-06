"""
Database Configuration
SQLAlchemy database setup and session management.
Supports both PostgreSQL (full mode) and SQLite (lite mode).
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator

from lite.config import is_lite_mode, get_data_path

# Select database URL based on backend mode
if is_lite_mode():
    _db_path = get_data_path("zerodb.db", is_dir=False)
    DATABASE_URL = f"sqlite:///{_db_path}"
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        pool_pre_ping=True,
    )
else:
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
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20
    )

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create Base class for models
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency for database sessions

    Yields:
        Session: SQLAlchemy database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
