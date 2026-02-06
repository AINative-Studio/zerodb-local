"""
Database Service
Handles PostgreSQL database operations

Issue #1092: Added PgBouncer-optimized pool configuration to prevent
connection pool exhaustion causing 30-35s query latency.
"""
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from typing import Optional, Dict, Any

# Pool settings optimized for PgBouncer on Railway
# Matches main app config in src/backend/app/db/session.py
POOL_SIZE = int(os.getenv("ZERODB_POOL_SIZE", "10"))
MAX_OVERFLOW = int(os.getenv("ZERODB_MAX_OVERFLOW", "10"))
POOL_TIMEOUT = int(os.getenv("ZERODB_POOL_TIMEOUT", "5"))
POOL_RECYCLE = int(os.getenv("ZERODB_POOL_RECYCLE", "1200"))
CONNECT_TIMEOUT = int(os.getenv("ZERODB_CONNECT_TIMEOUT", "10"))


class DatabaseService:
    """
    Service for PostgreSQL database operations
    Uses pgvector extension for vector storage backup
    """

    def __init__(self):
        database_url = os.getenv(
            "DATABASE_URL",
            "postgresql://zerodb:localpass@postgres:5432/zerodb_local"
        )

        engine_kwargs = {
            "pool_pre_ping": True,
            "pool_size": POOL_SIZE,
            "max_overflow": MAX_OVERFLOW,
            "pool_timeout": POOL_TIMEOUT,
            "pool_recycle": POOL_RECYCLE,
            "connect_args": {
                "connect_timeout": CONNECT_TIMEOUT,
                "application_name": "zerodb_tables",
            },
        }

        # Railway/PgBouncer optimizations
        if "railway" in database_url.lower() or "proxy.rlwy.net" in database_url:
            engine_kwargs["pool_reset_on_return"] = "commit"

        self.engine = create_engine(database_url, **engine_kwargs)
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )

    def get_db(self):
        """
        Get database session
        Use with FastAPI Depends for dependency injection
        """
        db = self.SessionLocal()
        try:
            yield db
        finally:
            db.close()

    async def health_check(self) -> Dict[str, Any]:
        """
        Check PostgreSQL health

        Returns:
            Health status dict
        """
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                result.fetchone()

            return {
                "status": "healthy",
                "message": "Database connection successful"
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }


# Global instance
database_service = DatabaseService()
