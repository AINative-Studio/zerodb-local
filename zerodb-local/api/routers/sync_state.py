"""
Sync State Router
API endpoints for managing sync state tracking
"""
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

# Import schemas
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from schemas.sync_state import (
    SyncStateCreate,
    SyncStateUpdate,
    SyncStateResponse,
    SyncStateListResponse
)

# Import service
from services.sync_state_service import SyncStateService
from services.database_service import database_service

# Import authentication (when available)
try:
    from app.api.deps import get_current_user_flexible
    from app.models.user import User
except ImportError:
    # Fallback for isolated testing
    class MockUser:
        def __init__(self):
            self.id = "00000000-0000-0000-0000-000000000001"
            self.email = "dev@localhost"

    User = MockUser

    def get_current_user_flexible():
        return lambda: MockUser()


router = APIRouter()


def get_sync_state_service(db: Session = Depends(database_service.get_db)) -> SyncStateService:
    """Dependency to get SyncStateService instance"""
    return SyncStateService(db)


@router.get("/state", response_model=SyncStateResponse)
async def get_sync_state(
    project_id: UUID,
    entity_type: str = Query(..., description="Entity type (vectors, tables, memory, files, events)"),
    current_user: User = Depends(get_current_user_flexible),
    service: SyncStateService = Depends(get_sync_state_service)
):
    """
    Get sync state for a specific entity type

    **Authentication:** Required

    **Path Parameters:**
    - project_id: Project UUID

    **Query Parameters:**
    - entity_type: Entity type to get sync state for

    **Returns:**
    - Sync state information including watermark and timestamps
    """
    sync_state = service.get_sync_state(project_id, entity_type)

    if not sync_state:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sync state not found for entity type '{entity_type}'"
        )

    return SyncStateResponse.model_validate(sync_state)


@router.get("/state/list", response_model=SyncStateListResponse)
async def list_sync_states(
    project_id: UUID,
    current_user: User = Depends(get_current_user_flexible),
    service: SyncStateService = Depends(get_sync_state_service)
):
    """
    List all sync states for a project

    **Authentication:** Required

    **Path Parameters:**
    - project_id: Project UUID

    **Returns:**
    - List of all sync states for the project
    """
    sync_states = service.list_sync_states(project_id)

    return SyncStateListResponse(
        items=[SyncStateResponse.model_validate(ss) for ss in sync_states],
        total=len(sync_states),
        project_id=project_id
    )


@router.post("/state", response_model=SyncStateResponse, status_code=status.HTTP_201_CREATED)
async def create_sync_state(
    project_id: UUID,
    data: SyncStateCreate,
    current_user: User = Depends(get_current_user_flexible),
    service: SyncStateService = Depends(get_sync_state_service)
):
    """
    Create a new sync state

    **Authentication:** Required

    **Path Parameters:**
    - project_id: Project UUID

    **Body:**
    - entity_type: Entity type to track
    - sync_strategy: Sync strategy (full, incremental, selective)
    - sync_direction: Sync direction (push, pull, bidirectional)
    - watermark: Initial watermark data (optional)

    **Returns:**
    - Created sync state
    """
    # Check if sync state already exists
    existing = service.get_sync_state(data.project_id, data.entity_type)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Sync state already exists for entity type '{data.entity_type}'"
        )

    # Create new sync state
    sync_state = service.get_or_create_sync_state(
        project_id=data.project_id,
        entity_type=data.entity_type,
        sync_strategy=data.sync_strategy,
        sync_direction=data.sync_direction
    )

    # Update with initial watermark if provided
    if data.watermark:
        sync_state = service.update_watermark(
            project_id=data.project_id,
            entity_type=data.entity_type,
            watermark_data=data.watermark
        )

    return SyncStateResponse.model_validate(sync_state)


@router.put("/state", response_model=SyncStateResponse)
async def update_sync_state(
    project_id: UUID,
    entity_type: str = Query(..., description="Entity type to update"),
    data: SyncStateUpdate = None,
    current_user: User = Depends(get_current_user_flexible),
    service: SyncStateService = Depends(get_sync_state_service)
):
    """
    Update sync state

    **Authentication:** Required

    **Path Parameters:**
    - project_id: Project UUID

    **Query Parameters:**
    - entity_type: Entity type to update

    **Body:**
    - last_sync_at: Last sync timestamp (optional)
    - last_cloud_export_id: Last cloud export ID (optional)
    - last_cloud_import_id: Last cloud import ID (optional)
    - watermark: Updated watermark data (optional)
    - sync_strategy: Updated strategy (optional)
    - sync_direction: Updated direction (optional)

    **Returns:**
    - Updated sync state
    """
    # Check if sync state exists
    existing = service.get_sync_state(project_id, entity_type)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sync state not found for entity type '{entity_type}'"
        )

    # Update sync state
    sync_state = service.update_sync_state(
        project_id=project_id,
        entity_type=entity_type,
        watermark=data.watermark if data else None,
        last_cloud_export_id=data.last_cloud_export_id if data else None,
        last_cloud_import_id=data.last_cloud_import_id if data else None,
        sync_strategy=data.sync_strategy if data else None,
        sync_direction=data.sync_direction if data else None
    )

    return SyncStateResponse.model_validate(sync_state)


@router.delete("/state")
async def delete_sync_state(
    project_id: UUID,
    entity_type: Optional[str] = Query(None, description="Entity type to delete (if None, deletes all)"),
    current_user: User = Depends(get_current_user_flexible),
    service: SyncStateService = Depends(get_sync_state_service)
):
    """
    Reset sync state by deleting records

    **Authentication:** Required

    **Path Parameters:**
    - project_id: Project UUID

    **Query Parameters:**
    - entity_type: Optional entity type (if not provided, deletes all sync states)

    **Returns:**
    - Number of records deleted
    """
    deleted_count = service.reset_sync_state(project_id, entity_type)

    if deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No sync states found to delete"
        )

    return {
        "message": f"Deleted {deleted_count} sync state(s)",
        "deleted_count": deleted_count,
        "project_id": str(project_id),
        "entity_type": entity_type
    }
