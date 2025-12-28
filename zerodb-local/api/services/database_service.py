"""
Database Service
Handles PostgreSQL database operations
"""
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from typing import Optional, Dict, Any


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
        self.engine = create_engine(database_url, pool_pre_ping=True)
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
