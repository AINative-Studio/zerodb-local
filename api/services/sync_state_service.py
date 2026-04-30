"""
Sync State Service
Business logic for managing sync state tracking
"""
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import select, delete

from models.sync_state import SyncState


class SyncStateService:
    """
    Service for managing sync state operations

    Provides methods for tracking sync state between local and cloud,
    including watermark management for incremental sync.
    """

    def __init__(self, db: Session):
        """
        Initialize service with database session

        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    def get_sync_state(
        self,
        project_id: UUID,
        entity_type: str
    ) -> Optional[SyncState]:
        """
        Get sync state for a specific entity type in a project

        Args:
            project_id: Project UUID
            entity_type: Entity type (vectors, tables, memory, files, events)

        Returns:
            SyncState object if found, None otherwise
        """
        stmt = select(SyncState).where(
            SyncState.project_id == project_id,
            SyncState.entity_type == entity_type
        )
        result = self.db.execute(stmt)
        return result.scalar_one_or_none()

    def get_or_create_sync_state(
        self,
        project_id: UUID,
        entity_type: str,
        sync_strategy: str = "full",
        sync_direction: str = "bidirectional"
    ) -> SyncState:
        """
        Get existing sync state or create new one if it doesn't exist

        Args:
            project_id: Project UUID
            entity_type: Entity type
            sync_strategy: Default sync strategy if creating new
            sync_direction: Default sync direction if creating new

        Returns:
            SyncState object
        """
        sync_state = self.get_sync_state(project_id, entity_type)

        if not sync_state:
            sync_state = SyncState(
                project_id=project_id,
                entity_type=entity_type,
                sync_strategy=sync_strategy,
                sync_direction=sync_direction,
                watermark={}
            )
            self.db.add(sync_state)
            self.db.commit()
            self.db.refresh(sync_state)

        return sync_state

    def update_sync_state(
        self,
        project_id: UUID,
        entity_type: str,
        watermark: Optional[Dict[str, Any]] = None,
        last_cloud_export_id: Optional[UUID] = None,
        last_cloud_import_id: Optional[UUID] = None,
        sync_strategy: Optional[str] = None,
        sync_direction: Optional[str] = None
    ) -> SyncState:
        """
        Update or create sync state with new values

        Args:
            project_id: Project UUID
            entity_type: Entity type
            watermark: Updated watermark data
            last_cloud_export_id: Last cloud export operation ID
            last_cloud_import_id: Last cloud import operation ID
            sync_strategy: Updated sync strategy
            sync_direction: Updated sync direction

        Returns:
            Updated SyncState object
        """
        sync_state = self.get_sync_state(project_id, entity_type)

        if not sync_state:
            # Create new sync state
            sync_state = SyncState(
                project_id=project_id,
                entity_type=entity_type,
                sync_strategy=sync_strategy or "full",
                sync_direction=sync_direction or "bidirectional",
                watermark=watermark or {},
                last_sync_at=datetime.utcnow()
            )
            self.db.add(sync_state)
        else:
            # Update existing sync state
            if watermark is not None:
                sync_state.watermark = watermark
            if last_cloud_export_id is not None:
                sync_state.last_cloud_export_id = last_cloud_export_id
            if last_cloud_import_id is not None:
                sync_state.last_cloud_import_id = last_cloud_import_id
            if sync_strategy is not None:
                sync_state.sync_strategy = sync_strategy
            if sync_direction is not None:
                sync_state.sync_direction = sync_direction

            sync_state.last_sync_at = datetime.utcnow()
            sync_state.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(sync_state)
        return sync_state

    def list_sync_states(self, project_id: UUID) -> List[SyncState]:
        """
        List all sync states for a project

        Args:
            project_id: Project UUID

        Returns:
            List of SyncState objects
        """
        stmt = select(SyncState).where(
            SyncState.project_id == project_id
        ).order_by(SyncState.entity_type)

        result = self.db.execute(stmt)
        return list(result.scalars().all())

    def reset_sync_state(
        self,
        project_id: UUID,
        entity_type: Optional[str] = None
    ) -> int:
        """
        Reset sync state by deleting records

        Args:
            project_id: Project UUID
            entity_type: Optional entity type (if None, resets all)

        Returns:
            Number of records deleted
        """
        if entity_type:
            # Delete specific entity type
            stmt = delete(SyncState).where(
                SyncState.project_id == project_id,
                SyncState.entity_type == entity_type
            )
        else:
            # Delete all sync states for project
            stmt = delete(SyncState).where(
                SyncState.project_id == project_id
            )

        result = self.db.execute(stmt)
        self.db.commit()
        return result.rowcount

    def update_watermark(
        self,
        project_id: UUID,
        entity_type: str,
        watermark_data: Dict[str, Any]
    ) -> SyncState:
        """
        Update only the watermark for a sync state

        This is a convenience method for the common case of just
        updating the watermark after a sync operation.

        Args:
            project_id: Project UUID
            entity_type: Entity type
            watermark_data: New watermark data

        Returns:
            Updated SyncState object
        """
        return self.update_sync_state(
            project_id=project_id,
            entity_type=entity_type,
            watermark=watermark_data
        )

    def get_watermark(
        self,
        project_id: UUID,
        entity_type: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get current watermark for an entity type

        Args:
            project_id: Project UUID
            entity_type: Entity type

        Returns:
            Watermark dict if sync state exists, None otherwise
        """
        sync_state = self.get_sync_state(project_id, entity_type)
        return sync_state.watermark if sync_state else None

    def has_synced_before(
        self,
        project_id: UUID,
        entity_type: str
    ) -> bool:
        """
        Check if entity type has been synced before

        Args:
            project_id: Project UUID
            entity_type: Entity type

        Returns:
            True if sync state exists with last_sync_at, False otherwise
        """
        sync_state = self.get_sync_state(project_id, entity_type)
        return bool(sync_state and sync_state.last_sync_at)
