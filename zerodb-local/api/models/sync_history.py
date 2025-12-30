"""
SQLAlchemy model for sync history and audit logging
"""
from sqlalchemy import Column, String, Integer, BigInteger, Text, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB, TIMESTAMP
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
from uuid import uuid4
import uuid

Base = declarative_base()


class SyncHistory(Base):
    """
    Sync history model for audit trail

    Tracks all sync operations including:
    - Push/pull/bidirectional syncs
    - Full/incremental/selective modes
    - Success/failure status
    - Records synced per entity type
    - Bytes transferred
    - Error details
    - Rollback snapshots
    """

    __tablename__ = "sync_history"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)

    # Foreign keys
    project_id = Column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Sync identification
    sync_id = Column(UUID(as_uuid=True), unique=True, nullable=False, index=True)

    # Sync configuration
    direction = Column(
        String(20),
        nullable=False,
        comment="Sync direction: push/pull/bidirectional"
    )
    mode = Column(
        String(20),
        nullable=False,
        comment="Sync mode: full/incremental/selective"
    )

    # Status and timing
    status = Column(
        String(20),
        nullable=False,
        default="pending",
        index=True,
        comment="Sync status: pending/running/completed/failed/rolled_back"
    )
    started_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        index=True
    )
    completed_at = Column(TIMESTAMP(timezone=True))

    # Results
    records_synced = Column(
        JSONB,
        nullable=False,
        default={},
        comment="Per-entity record counts: {vectors: 500, tables: 150}"
    )
    bytes_transferred = Column(BigInteger, default=0)

    # Error handling
    error_message = Column(Text)
    error_stack = Column(Text)

    # Rollback support
    snapshot_id = Column(UUID(as_uuid=True))

    # Timestamps
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, default=datetime.utcnow)

    # Indexes (defined at class level for SQLAlchemy)
    __table_args__ = (
        Index('idx_sync_history_project_started', 'project_id', 'started_at'),
        Index('idx_sync_history_records_synced', 'records_synced', postgresql_using='gin'),
    )

    @property
    def duration_seconds(self) -> float:
        """Calculate sync duration in seconds"""
        if self.completed_at and self.started_at:
            delta = self.completed_at - self.started_at
            return delta.total_seconds()
        return 0.0

    @property
    def total_records_synced(self) -> int:
        """Calculate total records synced across all entity types"""
        if not self.records_synced:
            return 0
        return sum(self.records_synced.values())

    def to_dict(self) -> dict:
        """Convert model to dictionary"""
        return {
            "id": str(self.id),
            "project_id": str(self.project_id),
            "sync_id": str(self.sync_id),
            "direction": self.direction,
            "mode": self.mode,
            "status": self.status,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
            "records_synced": self.records_synced,
            "bytes_transferred": self.bytes_transferred,
            "error_message": self.error_message,
            "snapshot_id": str(self.snapshot_id) if self.snapshot_id else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

    def __repr__(self) -> str:
        return (
            f"<SyncHistory("
            f"sync_id={self.sync_id}, "
            f"direction={self.direction}, "
            f"status={self.status}, "
            f"records={self.total_records_synced}"
            f")>"
        )
