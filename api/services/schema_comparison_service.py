"""
Schema Comparison Cache Service
Manages caching of schema comparison results
"""
from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import text
import logging

from models.schema_comparison import SchemaComparison
from schemas.schema_diff import (
    SchemaDefinition,
    SchemaDiff,
    MigrationPlan,
    SchemaCompareResponse
)

logger = logging.getLogger(__name__)


class SchemaComparisonService:
    """
    Service for managing schema comparison cache

    Responsibilities:
    - Store schema comparison results
    - Retrieve cached comparisons
    - Invalidate expired comparisons
    - Provide breaking changes history
    """

    def __init__(self, cache_ttl_hours: int = 24):
        """
        Initialize schema comparison service

        Args:
            cache_ttl_hours: Time-to-live for cached comparisons in hours
        """
        self.cache_ttl_hours = cache_ttl_hours

    def save_comparison(
        self,
        db: Session,
        project_id: UUID,
        local_schema: SchemaDefinition,
        cloud_schema: SchemaDefinition,
        diff: SchemaDiff,
        migration_plan: Optional[MigrationPlan],
        comparison_summary: str
    ) -> SchemaComparison:
        """
        Save schema comparison to cache

        Args:
            db: Database session
            project_id: Project UUID
            local_schema: Local schema definition
            cloud_schema: Cloud schema definition
            diff: Schema diff result
            migration_plan: Optional migration plan
            comparison_summary: Human-readable summary

        Returns:
            SchemaComparison record
        """
        logger.info(f"Saving schema comparison for project {project_id}")

        # Calculate expiration
        expires_at = datetime.utcnow() + timedelta(hours=self.cache_ttl_hours)

        # Create comparison record
        comparison = SchemaComparison(
            project_id=project_id,
            local_schema=local_schema.model_dump(mode='json'),
            cloud_schema=cloud_schema.model_dump(mode='json'),
            diff_result=diff.model_dump(mode='json'),
            total_changes=diff.total_changes,
            has_breaking_changes=diff.has_breaking_changes,
            breaking_changes_count=len(diff.breaking_changes),
            migration_plan=migration_plan.model_dump(mode='json') if migration_plan else None,
            comparison_summary=comparison_summary,
            compared_at=datetime.utcnow(),
            expires_at=expires_at
        )

        db.add(comparison)
        db.commit()
        db.refresh(comparison)

        logger.info(
            f"Schema comparison saved: id={comparison.id}, "
            f"changes={comparison.total_changes}, "
            f"expires_at={expires_at}"
        )

        return comparison

    def get_latest_comparison(
        self,
        db: Session,
        project_id: UUID,
        include_expired: bool = False
    ) -> Optional[SchemaComparison]:
        """
        Get latest schema comparison for project

        Args:
            db: Database session
            project_id: Project UUID
            include_expired: Whether to include expired comparisons

        Returns:
            Latest SchemaComparison or None
        """
        query = text("""
            SELECT *
            FROM schema_comparisons
            WHERE project_id = :project_id
            AND (:include_expired OR expires_at IS NULL OR expires_at > NOW())
            ORDER BY compared_at DESC
            LIMIT 1
        """)

        result = db.execute(
            query,
            {
                "project_id": str(project_id),
                "include_expired": include_expired
            }
        ).first()

        if not result:
            return None

        # Map result to SchemaComparison object
        return db.query(SchemaComparison).filter(
            SchemaComparison.id == result.id
        ).first()

    def get_breaking_changes_history(
        self,
        db: Session,
        project_id: UUID,
        limit: int = 10
    ) -> list[Dict[str, Any]]:
        """
        Get history of comparisons with breaking changes

        Args:
            db: Database session
            project_id: Project UUID
            limit: Maximum records to return

        Returns:
            List of breaking change summaries
        """
        query = text("""
            SELECT
                id,
                compared_at,
                total_changes,
                breaking_changes_count,
                comparison_summary,
                diff_result->'breaking_changes' as breaking_changes
            FROM schema_comparisons
            WHERE project_id = :project_id
            AND has_breaking_changes = true
            ORDER BY compared_at DESC
            LIMIT :limit
        """)

        results = db.execute(
            query,
            {
                "project_id": str(project_id),
                "limit": limit
            }
        ).fetchall()

        return [
            {
                "id": str(row.id),
                "compared_at": row.compared_at.isoformat() if row.compared_at else None,
                "total_changes": row.total_changes,
                "breaking_changes_count": row.breaking_changes_count,
                "comparison_summary": row.comparison_summary,
                "breaking_changes": row.breaking_changes
            }
            for row in results
        ]

    def invalidate_expired(self, db: Session) -> int:
        """
        Delete expired schema comparisons

        Args:
            db: Database session

        Returns:
            Number of records deleted
        """
        query = text("""
            DELETE FROM schema_comparisons
            WHERE expires_at IS NOT NULL
            AND expires_at < NOW()
        """)

        result = db.execute(query)
        db.commit()

        deleted_count = result.rowcount
        logger.info(f"Invalidated {deleted_count} expired schema comparisons")

        return deleted_count

    def get_comparison_by_id(
        self,
        db: Session,
        comparison_id: UUID
    ) -> Optional[SchemaComparison]:
        """
        Get schema comparison by ID

        Args:
            db: Database session
            comparison_id: Comparison UUID

        Returns:
            SchemaComparison or None
        """
        return db.query(SchemaComparison).filter(
            SchemaComparison.id == comparison_id
        ).first()
