"""
Sync State Model
Tracks synchronization state for each entity type per project
"""
from datetime import datetime
from uuid import UUID, uuid4
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class SyncState(Base):
    """
    Model for tracking sync state between local and cloud

    Stores watermarks and metadata for incremental sync operations
    for each entity type (vectors, tables, memory, files, events) per project.
    """
    __tablename__ = "sync_state"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    project_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey('projects.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )

    # Entity identification
    entity_type = Column(
        String(50),
        nullable=False,
        index=True
    )  # 'vectors', 'tables', 'memory', 'files', 'events'

    # Sync timestamps
    last_sync_at = Column(DateTime, nullable=True)

    # Cloud sync tracking
    last_cloud_export_id = Column(PG_UUID(as_uuid=True), nullable=True)
    last_cloud_import_id = Column(PG_UUID(as_uuid=True), nullable=True)

    # Watermark for incremental sync
    # Structure varies by entity_type:
    # - vectors: {"last_vector_id": "uuid", "last_timestamp": "iso8601"}
    # - tables: {"table_id": {"last_row_id": "uuid", "last_timestamp": "iso8601"}}
    # - events: {"last_event_id": "uuid", "last_timestamp": "iso8601", "offset": 123}
    watermark = Column(JSONB, default={})

    # Sync configuration
    sync_strategy = Column(
        String(50),
        default='full',
        nullable=False
    )  # 'full', 'incremental', 'selective'

    sync_direction = Column(
        String(20),
        default='bidirectional',
        nullable=False
    )  # 'push', 'pull', 'bidirectional'

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return (
            f"<SyncState(id={self.id}, project_id={self.project_id}, "
            f"entity_type={self.entity_type}, strategy={self.sync_strategy})>"
        )

    def to_dict(self):
        """Convert model to dictionary"""
        return {
            "id": str(self.id),
            "project_id": str(self.project_id),
            "entity_type": self.entity_type,
            "last_sync_at": self.last_sync_at.isoformat() if self.last_sync_at else None,
            "last_cloud_export_id": str(self.last_cloud_export_id) if self.last_cloud_export_id else None,
            "last_cloud_import_id": str(self.last_cloud_import_id) if self.last_cloud_import_id else None,
            "watermark": self.watermark,
            "sync_strategy": self.sync_strategy,
            "sync_direction": self.sync_direction,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
