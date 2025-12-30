"""
Sync History API Router
RESTful endpoints for sync history and audit trail
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from uuid import UUID
from datetime import datetime

from db.session import get_db
from services.sync_history_service import SyncHistoryService
from schemas.sync_history import (
    SyncHistoryResponse,
    SyncHistoryListResponse,
    SyncHistoryStats,
    CleanupResult,
    SyncHistoryFilter,
    SyncDirection,
    SyncMode,
    SyncStatus,
    SyncHistoryDetailResponse
)

router = APIRouter(prefix="/v1/projects/{project_id}/sync/history", tags=["sync-history"])


@router.get("", response_model=SyncHistoryListResponse)
async def list_sync_history(
    project_id: UUID,
    direction: Optional[SyncDirection] = Query(None, description="Filter by sync direction"),
    mode: Optional[SyncMode] = Query(None, description="Filter by sync mode"),
    status: Optional[SyncStatus] = Query(None, description="Filter by status"),
    start_date: Optional[datetime] = Query(None, description="Filter syncs after this date"),
    end_date: Optional[datetime] = Query(None, description="Filter syncs before this date"),
    limit: int = Query(100, ge=1, le=1000, description="Results per page"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    db: Session = Depends(get_db)
):
    """
    List sync history for a project with filtering and pagination

    Query Parameters:
    - **direction**: Filter by sync direction (push/pull/bidirectional)
    - **mode**: Filter by sync mode (full/incremental/selective)
    - **status**: Filter by status (pending/running/completed/failed/rolled_back)
    - **start_date**: Only syncs started after this timestamp
    - **end_date**: Only syncs started before this timestamp
    - **limit**: Results per page (max 1000)
    - **offset**: Pagination offset

    Returns paginated list of sync history records ordered by most recent first.
    """
    service = SyncHistoryService(db)

    filters = SyncHistoryFilter(
        direction=direction,
        mode=mode,
        status=status,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset
    )

    return service.list_history(project_id, filters)


@router.get("/{sync_id}", response_model=SyncHistoryDetailResponse)
async def get_sync_history(
    project_id: UUID,
    sync_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get detailed sync history for a specific sync operation

    Path Parameters:
    - **project_id**: Project UUID
    - **sync_id**: Sync operation UUID

    Returns detailed sync history including:
    - Sync configuration (direction, mode)
    - Status and timing
    - Records synced per entity type
    - Bytes transferred
    - Error details (if failed)
    - Snapshot ID for rollback
    """
    service = SyncHistoryService(db)

    history = service.get_history(sync_id)

    if not history:
        raise HTTPException(
            status_code=404,
            detail=f"Sync history not found for sync_id: {sync_id}"
        )

    if history.project_id != project_id:
        raise HTTPException(
            status_code=403,
            detail="Sync does not belong to this project"
        )

    # Convert to detail response with total_records_synced
    response_data = history.to_dict()
    response_data['total_records_synced'] = history.total_records_synced

    return SyncHistoryDetailResponse(**response_data)


@router.get("/stats", response_model=SyncHistoryStats)
async def get_sync_stats(
    project_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get aggregated sync statistics for a project

    Path Parameters:
    - **project_id**: Project UUID

    Returns comprehensive statistics including:
    - Total syncs and success/failure counts
    - Last sync timestamps
    - Total records synced across all entity types
    - Total bytes transferred
    - Average sync duration
    - Per-direction breakdown (push/pull/bidirectional)
    - Per-entity-type totals
    """
    service = SyncHistoryService(db)

    return service.get_history_stats(project_id)


@router.delete("", response_model=CleanupResult)
async def cleanup_old_history(
    project_id: UUID,
    days: int = Query(30, ge=1, le=365, description="Delete entries older than this many days"),
    db: Session = Depends(get_db)
):
    """
    Delete old sync history entries to free up space

    Path Parameters:
    - **project_id**: Project UUID

    Query Parameters:
    - **days**: Delete entries older than this many days (default: 30, max: 365)

    Returns cleanup result including:
    - Number of deleted records
    - Date range of deleted records
    - Bytes freed

    Note: This operation is permanent and cannot be undone.
    """
    service = SyncHistoryService(db)

    return service.cleanup_old_history(project_id, days)


@router.get("/recent", response_model=list[SyncHistoryResponse])
async def get_recent_syncs(
    project_id: UUID,
    limit: int = Query(10, ge=1, le=50, description="Number of recent syncs"),
    db: Session = Depends(get_db)
):
    """
    Get most recent sync operations for a project

    Path Parameters:
    - **project_id**: Project UUID

    Query Parameters:
    - **limit**: Number of recent syncs to return (max 50)

    Returns list of recent syncs ordered by most recent first.
    Quick endpoint for checking recent sync activity.
    """
    service = SyncHistoryService(db)

    history = service.get_recent_syncs(project_id, limit)

    return [SyncHistoryResponse.model_validate(h) for h in history]


@router.get("/failed", response_model=list[SyncHistoryResponse])
async def get_failed_syncs(
    project_id: UUID,
    limit: int = Query(10, ge=1, le=50, description="Number of failed syncs"),
    db: Session = Depends(get_db)
):
    """
    Get recent failed sync operations for debugging

    Path Parameters:
    - **project_id**: Project UUID

    Query Parameters:
    - **limit**: Number of failed syncs to return (max 50)

    Returns list of failed syncs ordered by most recent first.
    Useful for debugging and troubleshooting sync issues.
    """
    service = SyncHistoryService(db)

    history = service.get_failed_syncs(project_id, limit)

    return [SyncHistoryResponse.model_validate(h) for h in history]
