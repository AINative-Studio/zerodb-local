"""
ChangeLog Model
Tracks all database changes for incremental sync
"""
from datetime import datetime
from uuid import UUID, uuid4
from sqlalchemy import Column, String, Boolean
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.ext.declarative import declarative_base

from models.types import LiteCompatibleDateTime as DateTime
from models.types import LiteCompatibleUUID

Base = declarative_base()


class ChangeLog(Base):
    """
    Model for tracking database changes (Change Data Capture)

    Automatically populated by database triggers on INSERT/UPDATE/DELETE
    operations on vectors, tables, files, events, and memory tables.
    Used for incremental sync between local and cloud.
    """
    __tablename__ = "change_log"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    # Refs #113: LiteCompatibleUUID, not plain PG_UUID -- see
    # api/models/sync_history.py's project_id for the full explanation
    # (lite/db/schema_lite.sql's change_log.project_id REFERENCES
    # projects(id), a dashed-string TEXT column in lite mode; plain
    # PG_UUID's SQLite bind encoding is hex-only, so filtering by this
    # column would silently match nothing against real, FK-valid data).
    project_id = Column(LiteCompatibleUUID(), nullable=False, index=True)

    # Entity identification
    entity_type = Column(String(50), nullable=False, index=True)  # 'vector', 'table_row', 'file', 'event', 'memory'
    entity_id = Column(PG_UUID(as_uuid=True), nullable=False)

    # Operation details
    operation = Column(String(10), nullable=False)  # 'INSERT', 'UPDATE', 'DELETE'
    data = Column(JSONB)  # Full row data as JSON

    # Timestamps
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    synced_at = Column(DateTime, nullable=True)

    # Sync tracking
    synced = Column(Boolean, nullable=False, default=False, index=True)

    def __repr__(self):
        return (
            f"<ChangeLog(id={self.id}, project_id={self.project_id}, "
            f"entity_type={self.entity_type}, entity_id={self.entity_id}, "
            f"operation={self.operation}, synced={self.synced})>"
        )

    def to_dict(self):
        """Convert model to dictionary"""
        return {
            "id": str(self.id),
            "project_id": str(self.project_id),
            "entity_type": self.entity_type,
            "entity_id": str(self.entity_id),
            "operation": self.operation,
            "data": self.data,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "synced_at": self.synced_at.isoformat() if self.synced_at else None,
            "synced": self.synced
        }
