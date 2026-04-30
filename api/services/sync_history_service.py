"""
Sync History Service
Manages sync history tracking and audit logging
"""
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_, or_
import logging

from models.sync_history import SyncHistory
from schemas.sync_history import (
    SyncHistoryCreate,
    SyncHistoryUpdate,
    SyncHistoryResponse,
    SyncHistoryListResponse,
    SyncHistoryStats,
    CleanupResult,
    SyncHistoryFilter,
    SyncDirection,
    SyncMode,
    SyncStatus
)

logger = logging.getLogger(__name__)


class SyncHistoryService:
    """
    Service for managing sync history and audit trail

    Responsibilities:
    - Create history entries at sync start
    - Update entries during/after sync
    - Query history with filtering
    - Calculate statistics
    - Cleanup old entries
    """

    def __init__(self, db: Session):
        """
        Initialize sync history service

        Args:
            db: Database session
        """
        self.db = db

    def create_history_entry(
        self,
        project_id: UUID,
        sync_id: UUID,
        direction: SyncDirection,
        mode: SyncMode = SyncMode.INCREMENTAL,
        snapshot_id: Optional[UUID] = None
    ) -> SyncHistory:
        """
        Create a new sync history entry

        Args:
            project_id: Project UUID
            sync_id: Unique sync operation ID
            direction: Sync direction (push/pull/bidirectional)
            mode: Sync mode (full/incremental/selective)
            snapshot_id: Optional snapshot ID for rollback

        Returns:
            Created SyncHistory record
        """
        logger.info(
            f"Creating sync history entry: "
            f"sync_id={sync_id}, direction={direction}, mode={mode}"
        )

        history_entry = SyncHistory(
            project_id=project_id,
            sync_id=sync_id,
            direction=direction.value if isinstance(direction, SyncDirection) else direction,
            mode=mode.value if isinstance(mode, SyncMode) else mode,
            status=SyncStatus.PENDING.value,
            snapshot_id=snapshot_id,
            started_at=datetime.utcnow(),
            records_synced={}
        )

        self.db.add(history_entry)
        self.db.commit()
        self.db.refresh(history_entry)

        logger.info(f"Created sync history entry with ID: {history_entry.id}")
        return history_entry

    def update_history(
        self,
        sync_id: UUID,
        status: Optional[SyncStatus] = None,
        completed_at: Optional[datetime] = None,
        records_synced: Optional[Dict[str, int]] = None,
        bytes_transferred: Optional[int] = None,
        error_message: Optional[str] = None,
        error_stack: Optional[str] = None,
        snapshot_id: Optional[UUID] = None
    ) -> SyncHistory:
        """
        Update existing sync history entry

        Args:
            sync_id: Sync operation ID
            status: New status
            completed_at: Completion timestamp
            records_synced: Per-entity-type record counts
            bytes_transferred: Total bytes transferred
            error_message: Error message if failed
            error_stack: Error stack trace if failed
            snapshot_id: Snapshot ID for rollback

        Returns:
            Updated SyncHistory record
        """
        logger.info(f"Updating sync history: sync_id={sync_id}, status={status}")

        history_entry = self.db.query(SyncHistory).filter(
            SyncHistory.sync_id == sync_id
        ).first()

        if not history_entry:
            raise ValueError(f"Sync history not found for sync_id: {sync_id}")

        # Update fields if provided
        if status is not None:
            history_entry.status = status.value if isinstance(status, SyncStatus) else status
        if completed_at is not None:
            history_entry.completed_at = completed_at
        if records_synced is not None:
            history_entry.records_synced = records_synced
        if bytes_transferred is not None:
            history_entry.bytes_transferred = bytes_transferred
        if error_message is not None:
            history_entry.error_message = error_message
        if error_stack is not None:
            history_entry.error_stack = error_stack
        if snapshot_id is not None:
            history_entry.snapshot_id = snapshot_id

        history_entry.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(history_entry)

        logger.info(f"Updated sync history: {history_entry.id}")
        return history_entry

    def get_history(self, sync_id: UUID) -> Optional[SyncHistory]:
        """
        Get sync history by sync_id

        Args:
            sync_id: Sync operation ID

        Returns:
            SyncHistory record or None
        """
        return self.db.query(SyncHistory).filter(
            SyncHistory.sync_id == sync_id
        ).first()

    def list_history(
        self,
        project_id: UUID,
        filters: Optional[SyncHistoryFilter] = None
    ) -> SyncHistoryListResponse:
        """
        List sync history with filtering and pagination

        Args:
            project_id: Project UUID
            filters: Optional filter parameters

        Returns:
            Paginated list of sync history records
        """
        logger.info(f"Listing sync history for project: {project_id}")

        # Base query
        query = self.db.query(SyncHistory).filter(
            SyncHistory.project_id == project_id
        )

        # Apply filters if provided
        if filters:
            if filters.direction:
                query = query.filter(SyncHistory.direction == filters.direction.value)
            if filters.mode:
                query = query.filter(SyncHistory.mode == filters.mode.value)
            if filters.status:
                query = query.filter(SyncHistory.status == filters.status.value)
            if filters.start_date:
                query = query.filter(SyncHistory.started_at >= filters.start_date)
            if filters.end_date:
                query = query.filter(SyncHistory.started_at <= filters.end_date)

        # Get total count
        total = query.count()

        # Apply pagination and ordering
        limit = filters.limit if filters else 100
        offset = filters.offset if filters else 0

        items = query.order_by(
            desc(SyncHistory.started_at)
        ).limit(limit).offset(offset).all()

        has_more = (offset + limit) < total

        return SyncHistoryListResponse(
            items=[SyncHistoryResponse.model_validate(item) for item in items],
            total=total,
            limit=limit,
            offset=offset,
            has_more=has_more
        )

    def get_history_stats(self, project_id: UUID) -> SyncHistoryStats:
        """
        Get aggregated sync statistics for a project

        Args:
            project_id: Project UUID

        Returns:
            Aggregated statistics
        """
        logger.info(f"Calculating sync statistics for project: {project_id}")

        # Count total syncs
        total_syncs = self.db.query(func.count(SyncHistory.id)).filter(
            SyncHistory.project_id == project_id
        ).scalar() or 0

        # Count by status
        successful_syncs = self.db.query(func.count(SyncHistory.id)).filter(
            and_(
                SyncHistory.project_id == project_id,
                SyncHistory.status == SyncStatus.COMPLETED.value
            )
        ).scalar() or 0

        failed_syncs = self.db.query(func.count(SyncHistory.id)).filter(
            and_(
                SyncHistory.project_id == project_id,
                SyncHistory.status == SyncStatus.FAILED.value
            )
        ).scalar() or 0

        rolled_back_syncs = self.db.query(func.count(SyncHistory.id)).filter(
            and_(
                SyncHistory.project_id == project_id,
                SyncHistory.status == SyncStatus.ROLLED_BACK.value
            )
        ).scalar() or 0

        # Count by direction
        push_syncs = self.db.query(func.count(SyncHistory.id)).filter(
            and_(
                SyncHistory.project_id == project_id,
                SyncHistory.direction == SyncDirection.PUSH.value
            )
        ).scalar() or 0

        pull_syncs = self.db.query(func.count(SyncHistory.id)).filter(
            and_(
                SyncHistory.project_id == project_id,
                SyncHistory.direction == SyncDirection.PULL.value
            )
        ).scalar() or 0

        bidirectional_syncs = self.db.query(func.count(SyncHistory.id)).filter(
            and_(
                SyncHistory.project_id == project_id,
                SyncHistory.direction == SyncDirection.BIDIRECTIONAL.value
            )
        ).scalar() or 0

        # Get last sync timestamp
        last_sync = self.db.query(SyncHistory).filter(
            SyncHistory.project_id == project_id
        ).order_by(desc(SyncHistory.started_at)).first()

        last_sync_at = last_sync.started_at if last_sync else None

        # Get last successful sync timestamp
        last_successful_sync = self.db.query(SyncHistory).filter(
            and_(
                SyncHistory.project_id == project_id,
                SyncHistory.status == SyncStatus.COMPLETED.value
            )
        ).order_by(desc(SyncHistory.started_at)).first()

        last_successful_sync_at = (
            last_successful_sync.started_at if last_successful_sync else None
        )

        # Calculate totals using raw SQL for JSONB aggregation
        # This aggregates all records_synced JSONB fields
        totals_query = self.db.query(
            func.sum(SyncHistory.bytes_transferred).label('total_bytes')
        ).filter(
            SyncHistory.project_id == project_id
        ).first()

        total_bytes_transferred = int(totals_query.total_bytes or 0)

        # Calculate total records synced across all entity types
        # For this we need to iterate since JSONB sum is complex
        all_records = self.db.query(SyncHistory.records_synced).filter(
            SyncHistory.project_id == project_id
        ).all()

        total_records_synced = 0
        entity_type_totals: Dict[str, int] = {}

        for record in all_records:
            if record.records_synced:
                for entity_type, count in record.records_synced.items():
                    total_records_synced += count
                    entity_type_totals[entity_type] = (
                        entity_type_totals.get(entity_type, 0) + count
                    )

        # Calculate average sync duration
        completed_syncs = self.db.query(SyncHistory).filter(
            and_(
                SyncHistory.project_id == project_id,
                SyncHistory.status == SyncStatus.COMPLETED.value,
                SyncHistory.completed_at.isnot(None)
            )
        ).all()

        if completed_syncs:
            durations = [
                (sync.completed_at - sync.started_at).total_seconds()
                for sync in completed_syncs
                if sync.completed_at
            ]
            avg_sync_duration_seconds = (
                sum(durations) / len(durations) if durations else None
            )
        else:
            avg_sync_duration_seconds = None

        # Calculate average bytes per sync
        avg_bytes_per_sync = (
            total_bytes_transferred / total_syncs if total_syncs > 0 else None
        )

        return SyncHistoryStats(
            project_id=project_id,
            total_syncs=total_syncs,
            successful_syncs=successful_syncs,
            failed_syncs=failed_syncs,
            rolled_back_syncs=rolled_back_syncs,
            last_sync_at=last_sync_at,
            last_successful_sync_at=last_successful_sync_at,
            total_records_synced=total_records_synced,
            total_bytes_transferred=total_bytes_transferred,
            avg_sync_duration_seconds=avg_sync_duration_seconds,
            avg_bytes_per_sync=avg_bytes_per_sync,
            push_syncs=push_syncs,
            pull_syncs=pull_syncs,
            bidirectional_syncs=bidirectional_syncs,
            entity_type_totals=entity_type_totals
        )

    def cleanup_old_history(
        self,
        project_id: Optional[UUID] = None,
        days: int = 30
    ) -> CleanupResult:
        """
        Delete sync history older than specified days

        Args:
            project_id: Optional project UUID (None = all projects)
            days: Delete entries older than this many days

        Returns:
            CleanupResult with deletion details
        """
        logger.info(
            f"Cleaning up sync history older than {days} days "
            f"for project: {project_id or 'all'}"
        )

        cutoff_date = datetime.utcnow() - timedelta(days=days)

        # Build query
        query = self.db.query(SyncHistory).filter(
            SyncHistory.started_at < cutoff_date
        )

        if project_id:
            query = query.filter(SyncHistory.project_id == project_id)

        # Get records to delete for stats
        to_delete = query.all()

        if not to_delete:
            logger.info("No old sync history to clean up")
            return CleanupResult(
                deleted_count=0,
                oldest_deleted=None,
                newest_deleted=None,
                bytes_freed=0
            )

        # Calculate stats before deletion
        oldest_deleted = min(record.started_at for record in to_delete)
        newest_deleted = max(record.started_at for record in to_delete)
        bytes_freed = sum(record.bytes_transferred or 0 for record in to_delete)
        deleted_count = len(to_delete)

        # Delete records
        query.delete(synchronize_session=False)
        self.db.commit()

        logger.info(
            f"Cleaned up {deleted_count} sync history records, "
            f"freed {bytes_freed} bytes"
        )

        return CleanupResult(
            deleted_count=deleted_count,
            oldest_deleted=oldest_deleted,
            newest_deleted=newest_deleted,
            bytes_freed=bytes_freed
        )

    def get_recent_syncs(
        self,
        project_id: UUID,
        limit: int = 10
    ) -> List[SyncHistory]:
        """
        Get most recent syncs for a project

        Args:
            project_id: Project UUID
            limit: Number of recent syncs to return

        Returns:
            List of recent SyncHistory records
        """
        return self.db.query(SyncHistory).filter(
            SyncHistory.project_id == project_id
        ).order_by(
            desc(SyncHistory.started_at)
        ).limit(limit).all()

    def get_failed_syncs(
        self,
        project_id: UUID,
        limit: int = 10
    ) -> List[SyncHistory]:
        """
        Get recent failed syncs for debugging

        Args:
            project_id: Project UUID
            limit: Number of failed syncs to return

        Returns:
            List of failed SyncHistory records
        """
        return self.db.query(SyncHistory).filter(
            and_(
                SyncHistory.project_id == project_id,
                SyncHistory.status == SyncStatus.FAILED.value
            )
        ).order_by(
            desc(SyncHistory.started_at)
        ).limit(limit).all()
