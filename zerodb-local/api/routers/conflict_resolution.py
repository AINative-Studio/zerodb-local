"""
Conflict Resolution API Router

Provides endpoints for viewing and resolving conflicts detected during sync operations.
"""
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
from services.conflict_resolver import ConflictResolver, ConflictResolutionStrategy
from schemas.conflict_resolution import (
    Conflict,
    ConflictResolutionRequest,
    ConflictResolutionResponse,
    ConflictSummary,
    AutoResolveRequest,
    AutoResolveResponse
)
from models.conflict_log import ConflictLog
from auth import get_current_user, User

router = APIRouter(prefix="/v1/projects/{project_id}/sync/conflicts", tags=["conflicts"])


@router.get("/", response_model=List[dict])
async def list_conflicts(
    project_id: UUID,
    entity_type: Optional[str] = Query(None, description="Filter by entity type"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all conflicts for a project.

    Retrieves conflict history from the database, showing how conflicts
    were detected and resolved during sync operations.

    Query Parameters:
    - entity_type: Filter by entity type (vector, table_row, memory, etc.)
    - limit: Maximum number of results (1-1000)
    - offset: Pagination offset

    Returns:
        List of conflict log entries with resolution details
    """
    resolver = ConflictResolver(db)

    conflicts = resolver.get_conflicts(
        project_id=project_id,
        entity_type=entity_type,
        limit=limit,
        offset=offset
    )

    return [conflict.to_dict() for conflict in conflicts]


@router.get("/{conflict_id}", response_model=dict)
async def get_conflict(
    project_id: UUID,
    conflict_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get details of a specific conflict.

    Retrieves complete information about a conflict, including:
    - Local and cloud versions of the data
    - Resolution strategy used
    - Timestamps
    - Chosen version

    Returns:
        Conflict details as dictionary
    """
    conflict = db.query(ConflictLog).filter(
        ConflictLog.id == conflict_id,
        ConflictLog.project_id == project_id
    ).first()

    if not conflict:
        raise HTTPException(status_code=404, detail="Conflict not found")

    return conflict.to_dict()


@router.post("/{conflict_id}/resolve", response_model=dict)
async def resolve_conflict(
    project_id: UUID,
    conflict_id: UUID,
    request: ConflictResolutionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Resolve a specific conflict.

    Note: This endpoint is for manual resolution workflows.
    In the current implementation, conflicts are resolved automatically
    during sync operations. This endpoint allows re-resolution or
    manual override of previously resolved conflicts.

    Request Body:
    - strategy: Resolution strategy (local_wins, cloud_wins, newest_wins, manual)
    - manual_choice: For manual strategy, specify 'local' or 'cloud'
    - notes: Optional resolution notes

    Returns:
        Resolution result with chosen version
    """
    # Get the existing conflict
    conflict = db.query(ConflictLog).filter(
        ConflictLog.id == conflict_id,
        ConflictLog.project_id == project_id
    ).first()

    if not conflict:
        raise HTTPException(status_code=404, detail="Conflict not found")

    # Prepare conflict dict for resolver
    conflict_dict = {
        "entity_id": conflict.entity_id,
        "entity_type": conflict.entity_type,
        "local_version": conflict.local_version,
        "cloud_version": conflict.cloud_version,
        "detected_at": conflict.detected_at
    }

    # Resolve using specified strategy
    resolver = ConflictResolver(db)

    try:
        if request.strategy == ConflictResolutionStrategy.MANUAL and request.manual_choice:
            # For manual strategy with explicit choice
            if request.manual_choice == "local":
                resolution = {
                    "resolution": "manual",
                    "chosen_version": conflict.local_version,
                    "discarded_version": conflict.cloud_version
                }
            elif request.manual_choice == "cloud":
                resolution = {
                    "resolution": "manual",
                    "chosen_version": conflict.cloud_version,
                    "discarded_version": conflict.local_version
                }
            else:
                raise HTTPException(
                    status_code=400,
                    detail="manual_choice must be 'local' or 'cloud'"
                )
        else:
            resolution = resolver.resolve_conflict(conflict_dict, request.strategy)

        # Update conflict log
        conflict.resolution_strategy = request.strategy.value
        conflict.chosen_version = resolution["chosen_version"]

        if request.notes:
            conflict.notes = request.notes

        db.commit()

        return {
            "conflict_id": str(conflict_id),
            "resolved_data": resolution["chosen_version"],
            "strategy_used": request.strategy.value,
            "chosen_version": request.manual_choice or "auto",
            "resolved_at": conflict.resolved_at.isoformat()
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/resolve-all", response_model=dict)
async def resolve_all_conflicts(
    project_id: UUID,
    request: AutoResolveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Auto-resolve all unresolved conflicts using a strategy.

    Note: In current implementation, conflicts are logged after resolution.
    This endpoint is for bulk re-resolution scenarios or future
    implementation where conflicts can be in an "unresolved" state.

    Request Body:
    - strategy: Resolution strategy to apply
    - exclude_breaking: Skip breaking conflicts (future feature)
    - dry_run: Preview without applying changes

    Returns:
        Summary of resolution results
    """
    # In current implementation, all conflicts are already resolved
    # This is a placeholder for future enhancement where conflicts
    # can be in pending state

    conflicts = db.query(ConflictLog).filter(
        ConflictLog.project_id == project_id
    ).all()

    if request.dry_run:
        return {
            "project_id": str(project_id),
            "strategy_used": request.strategy.value,
            "total_conflicts": len(conflicts),
            "resolved_count": 0,
            "skipped_count": len(conflicts),
            "failed_count": 0,
            "resolutions": [],
            "errors": [],
            "dry_run": True
        }

    # Future: Implement actual bulk resolution
    return {
        "project_id": str(project_id),
        "strategy_used": request.strategy.value,
        "total_conflicts": len(conflicts),
        "resolved_count": 0,
        "skipped_count": len(conflicts),
        "failed_count": 0,
        "resolutions": [],
        "errors": ["Bulk re-resolution not implemented - conflicts are resolved during sync"]
    }


@router.get("/summary", response_model=dict)
async def get_conflict_summary(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get summary statistics of conflicts for a project.

    Returns aggregate statistics including:
    - Total conflicts resolved
    - Breakdown by entity type
    - Breakdown by resolution strategy used
    - Recent conflict trends

    Returns:
        Conflict summary statistics
    """
    resolver = ConflictResolver(db)
    summary = resolver.get_conflict_summary(project_id)

    # Add project_id and default fields for schema compliance
    return {
        "project_id": str(project_id),
        "total_conflicts": summary["total_conflicts"],
        "unresolved_conflicts": 0,  # Current model: all logged conflicts are resolved
        "resolved_conflicts": summary["total_conflicts"],
        "by_entity_type": summary["by_entity_type"],
        "by_conflict_type": {},  # Future: track conflict types
        "by_strategy": summary["by_strategy"],
        "breaking_conflicts": 0,  # Future feature
        "requires_manual_resolution": 0  # Current: all auto-resolved
    }
