"""
Change Detection Router
Handles CDC (Change Data Capture) operations
"""
from typing import Optional
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

# Import schemas
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from schemas.change_log import (
    ChangeLogEntry,
    ChangeLogQuery,
    ChangeLogResponse,
    ChangeCountResponse,
    MarkSyncedRequest,
    MarkSyncedResponse,
    CleanupRequest,
    CleanupResponse,
    EntityType
)

# Import authentication from core backend (when available)
from auth import get_current_user_flexible, User
# Import database and CDC services
from services.database_service import database_service
from services.cdc_service import CDCService


router = APIRouter()
cdc_service = CDCService()


@router.get("/changes", response_model=ChangeLogResponse)
async def get_changes(
    project_id: str = Query(..., description="Project ID"),
    entity_type: Optional[EntityType] = Query(None, description="Filter by entity type"),
    since: Optional[datetime] = Query(None, description="Get changes after this timestamp"),
    until: Optional[datetime] = Query(None, description="Get changes before this timestamp"),
    unsynced_only: bool = Query(False, description="Only return unsynced changes"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    current_user: User = Depends(get_current_user_flexible),
    db: Session = Depends(database_service.get_db)
):
    """
    Get change log entries for a project

    Retrieves database changes tracked by CDC triggers. Supports filtering by:
    - Entity type (vector, table_row, file, event, memory)
    - Timestamp range (since/until)
    - Sync status (unsynced_only)

    **Authentication:** Required

    **Returns:**
    - List of change log entries
    - Total count and pagination info
    """
    try:
        project_uuid = UUID(project_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid project ID format"
        )

    # Get changes based on filters
    if unsynced_only:
        changes = cdc_service.get_unsynced_changes(
            db,
            project_uuid,
            entity_type=entity_type.value if entity_type else None,
            limit=limit
        )
    elif since:
        if until:
            changes = cdc_service.get_changes_between(
                db,
                project_uuid,
                start=since,
                end=until,
                entity_type=entity_type.value if entity_type else None,
                limit=limit
            )
        else:
            changes = cdc_service.get_changes_since(
                db,
                project_uuid,
                since=since,
                entity_type=entity_type.value if entity_type else None,
                limit=limit
            )
    else:
        changes = cdc_service.get_changes(
            db,
            project_uuid,
            entity_type=entity_type.value if entity_type else None,
            limit=limit,
            offset=offset
        )

    # Get total count for pagination
    stats = cdc_service.get_change_count(
        db,
        project_uuid,
        entity_type=entity_type.value if entity_type else None
    )

    return ChangeLogResponse(
        changes=[ChangeLogEntry(**change) for change in changes],
        total=stats["total_changes"],
        has_more=(offset + len(changes)) < stats["total_changes"]
    )


@router.get("/changes/count", response_model=ChangeCountResponse)
async def get_change_count(
    project_id: str = Query(..., description="Project ID"),
    entity_type: Optional[EntityType] = Query(None, description="Filter by entity type"),
    current_user: User = Depends(get_current_user_flexible),
    db: Session = Depends(database_service.get_db)
):
    """
    Get change statistics for a project

    Returns counts and metadata about tracked changes including:
    - Total changes
    - Unsynced changes
    - Breakdown by entity type
    - Breakdown by operation type
    - Oldest/newest change timestamps

    **Authentication:** Required

    **Returns:**
    - Change statistics and counts
    """
    try:
        project_uuid = UUID(project_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid project ID format"
        )

    stats = cdc_service.get_change_count(
        db,
        project_uuid,
        entity_type=entity_type.value if entity_type else None
    )

    return ChangeCountResponse(**stats)


@router.post("/changes/mark-synced", response_model=MarkSyncedResponse)
async def mark_changes_synced(
    request: MarkSyncedRequest,
    current_user: User = Depends(get_current_user_flexible),
    db: Session = Depends(database_service.get_db)
):
    """
    Mark specific changes as synced

    Updates change log entries to indicate they have been successfully
    synced to cloud. Sets synced=true and records synced_at timestamp.

    **Authentication:** Required

    **Request Body:**
    - `change_ids`: List of change log entry IDs to mark as synced

    **Returns:**
    - Count of changes marked as synced
    - Timestamp when marked
    """
    if not request.change_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="change_ids list cannot be empty"
        )

    result = cdc_service.mark_synced(db, request.change_ids)

    return MarkSyncedResponse(
        synced_count=result["synced_count"],
        timestamp=datetime.fromisoformat(result["timestamp"])
    )


@router.delete("/changes", response_model=CleanupResponse)
async def cleanup_old_changes(
    project_id: str = Query(..., description="Project ID"),
    older_than_days: int = Query(30, ge=1, le=365, description="Delete changes older than this"),
    dry_run: bool = Query(False, description="Preview deletion without executing"),
    current_user: User = Depends(get_current_user_flexible),
    db: Session = Depends(database_service.get_db)
):
    """
    Clean up old synced changes

    Deletes synced change log entries older than specified days to prevent
    unbounded growth of the change log table.

    **Authentication:** Required

    **Query Parameters:**
    - `project_id`: Project to clean up
    - `older_than_days`: Delete synced changes older than this (default: 30)
    - `dry_run`: Preview what would be deleted without actually deleting

    **Returns:**
    - Count of changes deleted (or would be deleted in dry run)
    - Oldest timestamp deleted
    """
    try:
        project_uuid = UUID(project_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid project ID format"
        )

    result = cdc_service.cleanup_old_changes(
        db,
        project_id=project_uuid,
        days=older_than_days,
        dry_run=dry_run
    )

    return CleanupResponse(
        project_id=project_id,
        deleted_count=result["deleted_count"],
        oldest_deleted=datetime.fromisoformat(result["oldest_deleted"]) if result["oldest_deleted"] else None,
        dry_run=result["dry_run"]
    )
