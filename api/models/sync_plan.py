"""
Sync Plan Model
Stores generated sync plans for execution and validation
"""
from datetime import datetime
from uuid import UUID, uuid4
from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Boolean, Float, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB, ARRAY
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class SyncPlan(Base):
    """
    Model for storing sync plans

    Stores generated sync plans that can be executed later.
    Includes all steps, entity counts, warnings, and metadata
    needed for sync execution.
    """
    __tablename__ = "sync_plans"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    plan_id = Column(PG_UUID(as_uuid=True), nullable=False, unique=True, default=uuid4, index=True)
    project_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey('projects.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )

    # Plan metadata
    direction = Column(String(20), nullable=False)  # 'push' or 'pull'
    status = Column(
        String(20),
        nullable=False,
        default='pending',
        index=True
    )  # 'pending', 'approved', 'executing', 'completed', 'failed', 'expired'

    # Sync steps
    steps = Column(JSONB, nullable=False)  # List of SyncStep objects as JSON
    total_steps = Column(Integer, nullable=False, default=0)

    # Entity counts
    entity_counts = Column(JSONB, nullable=False)  # EntityCount object as JSON

    # Estimates
    estimated_duration_seconds = Column(Float, nullable=False, default=0.0)
    estimated_data_size_bytes = Column(Integer, nullable=False, default=0)

    # Schema changes
    schema_changes = Column(JSONB, nullable=False)  # SchemaChangeInfo object as JSON

    # Conflicts
    conflicts = Column(JSONB, nullable=False)  # ConflictInfo object as JSON

    # Warnings and flags
    warnings = Column(ARRAY(Text), nullable=False, default=[])
    requires_approval = Column(Boolean, nullable=False, default=False)
    can_rollback = Column(Boolean, nullable=False, default=True)

    # Approval tracking
    approved_by = Column(String(255), nullable=True)
    approved_at = Column(DateTime, nullable=True)

    # Execution tracking
    executed_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    sync_result_id = Column(PG_UUID(as_uuid=True), nullable=True)  # Link to SyncResult if executed

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    expires_at = Column(
        DateTime,
        nullable=True,
        index=True
    )  # Plans expire after 24 hours by default

    def __repr__(self):
        return (
            f"<SyncPlan(plan_id={self.plan_id}, project_id={self.project_id}, "
            f"direction={self.direction}, status={self.status}, steps={self.total_steps})>"
        )

    def to_dict(self):
        """Convert model to dictionary"""
        return {
            "id": str(self.id),
            "plan_id": str(self.plan_id),
            "project_id": str(self.project_id),
            "direction": self.direction,
            "status": self.status,
            "steps": self.steps,
            "total_steps": self.total_steps,
            "entity_counts": self.entity_counts,
            "estimated_duration_seconds": self.estimated_duration_seconds,
            "estimated_data_size_bytes": self.estimated_data_size_bytes,
            "schema_changes": self.schema_changes,
            "conflicts": self.conflicts,
            "warnings": self.warnings,
            "requires_approval": self.requires_approval,
            "can_rollback": self.can_rollback,
            "approved_by": self.approved_by,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "executed_at": self.executed_at.isoformat() if self.executed_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "sync_result_id": str(self.sync_result_id) if self.sync_result_id else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None
        }

    def is_expired(self) -> bool:
        """Check if plan has expired"""
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at

    def is_executable(self) -> bool:
        """Check if plan can be executed"""
        if self.is_expired():
            return False
        if self.status in ['executing', 'completed', 'failed', 'expired']:
            return False
        if self.requires_approval and not self.approved_at:
            return False
        return True
