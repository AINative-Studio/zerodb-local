"""
Schema Comparison Model
Stores cached schema comparison results for performance
"""
from datetime import datetime
from uuid import UUID, uuid4
from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Boolean, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class SchemaComparison(Base):
    """
    Model for caching schema comparison results

    Stores the result of schema diff operations to avoid
    recomputing comparisons for the same schemas.
    Includes both the diff results and optional migration plan.
    """
    __tablename__ = "schema_comparisons"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    project_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey('projects.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )

    # Schema snapshots
    local_schema = Column(JSONB, nullable=False)
    cloud_schema = Column(JSONB, nullable=False)

    # Comparison results
    diff_result = Column(JSONB, nullable=False)  # Complete SchemaDiff as JSON
    total_changes = Column(Integer, nullable=False, default=0)
    has_breaking_changes = Column(Boolean, nullable=False, default=False)
    breaking_changes_count = Column(Integer, nullable=False, default=0)

    # Migration plan (optional)
    migration_plan = Column(JSONB, nullable=True)  # Complete MigrationPlan as JSON

    # Summary for quick reference
    comparison_summary = Column(Text, nullable=True)

    # Timestamps
    compared_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    expires_at = Column(
        DateTime,
        nullable=True,
        index=True
    )  # Optional expiration for cache invalidation
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return (
            f"<SchemaComparison(id={self.id}, project_id={self.project_id}, "
            f"changes={self.total_changes}, breaking={self.has_breaking_changes})>"
        )

    def to_dict(self):
        """Convert model to dictionary"""
        return {
            "id": str(self.id),
            "project_id": str(self.project_id),
            "local_schema": self.local_schema,
            "cloud_schema": self.cloud_schema,
            "diff_result": self.diff_result,
            "total_changes": self.total_changes,
            "has_breaking_changes": self.has_breaking_changes,
            "breaking_changes_count": self.breaking_changes_count,
            "migration_plan": self.migration_plan,
            "comparison_summary": self.comparison_summary,
            "compared_at": self.compared_at.isoformat() if self.compared_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
