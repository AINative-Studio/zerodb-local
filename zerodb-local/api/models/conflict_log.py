"""
Conflict Log Model
Tracks all conflicts detected during sync and their resolutions
"""
from datetime import datetime
from uuid import UUID, uuid4
from sqlalchemy import Column, String, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class ConflictLog(Base):
    """
    Model for tracking conflict resolution history

    Stores information about conflicts detected during sync between
    local and cloud storage, and how they were resolved.
    """
    __tablename__ = "conflict_log"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    project_id = Column(PG_UUID(as_uuid=True), nullable=False, index=True)

    # Entity identification
    entity_type = Column(String(50), nullable=False)  # 'vector', 'table_row', 'memory', etc.
    entity_id = Column(String(512), nullable=False)

    # Conflict details
    local_version = Column(JSONB, nullable=False)
    cloud_version = Column(JSONB, nullable=False)

    # Resolution details
    resolution_strategy = Column(String(50), nullable=False)  # 'local_wins', 'cloud_wins', etc.
    chosen_version = Column(JSONB, nullable=False)

    # Timestamps
    detected_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    # Optional metadata
    metadata = Column(JSONB, default={})
    notes = Column(Text)

    def __repr__(self):
        return (
            f"<ConflictLog(id={self.id}, project_id={self.project_id}, "
            f"entity_type={self.entity_type}, entity_id={self.entity_id}, "
            f"resolution={self.resolution_strategy})>"
        )

    def to_dict(self):
        """Convert model to dictionary"""
        return {
            "id": str(self.id),
            "project_id": str(self.project_id),
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "local_version": self.local_version,
            "cloud_version": self.cloud_version,
            "resolution_strategy": self.resolution_strategy,
            "chosen_version": self.chosen_version,
            "detected_at": self.detected_at.isoformat() if self.detected_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "metadata": self.metadata,
            "notes": self.notes
        }
