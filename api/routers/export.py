"""
Export Router
API endpoints for export bundle creation and management
"""
import os
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Path, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from database import get_db
from schemas.export import (
    ExportCreate,
    ExportResponse,
    ExportPreview,
    ExportMetadata,
    RecordCounts,
    ExportStatus,
    ExportType
)
from services.export_service import export_service
from services.sync_state_service import SyncStateService
from services.schema_diff_service import SchemaDiffService

router = APIRouter(prefix="/v1/projects", tags=["export"])


@router.post("/{project_id}/sync/export", response_model=ExportResponse)
async def create_export(
    project_id: UUID = Path(..., description="Project UUID"),
    export_request: ExportCreate = ...,
    db: Session = Depends(get_db)
):
    """
    Create an export bundle for the project

    Supports three export modes:
    - **full**: Export all entities in the project
    - **incremental**: Export only changes since last sync
    - **selective**: Export specific entity types

    The export bundle is packaged as a ZIP file containing:
    - manifest.json (metadata, counts, file list)
    - schema.json (database schema)
    - vectors.jsonl (vector embeddings)
    - tables/{table_name}.jsonl (table data)
    - events.jsonl (event stream)
    - memory.jsonl (agent memory)
    - files/metadata.json (file metadata)

    Args:
        project_id: Project UUID
        export_request: Export configuration

    Returns:
        Export response with bundle path and metadata
    """
    try:
        # Initialize services with DB session
        sync_state_svc = SyncStateService(db)
        schema_diff_svc = SchemaDiffService()

        # Update export service with initialized services
        export_service.sync_state_service = sync_state_svc
        export_service.schema_diff_service = schema_diff_svc

        # Create export bundle
        result = await export_service.create_export_bundle(
            db=db,
            project_id=project_id,
            mode=export_request.export_type.value,
            entity_types=export_request.entity_types,
            since_timestamp=export_request.since_timestamp
        )

        # Build response
        return ExportResponse(
            export_id=result["export_id"],
            project_id=project_id,
            status=ExportStatus.COMPLETED,
            export_type=export_request.export_type,
            bundle_path=result["bundle_path"],
            metadata=result["metadata"],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create export bundle: {str(e)}"
        )


@router.get("/{project_id}/sync/export/{export_id}")
async def download_export(
    project_id: UUID = Path(..., description="Project UUID"),
    export_id: UUID = Path(..., description="Export UUID"),
    db: Session = Depends(get_db)
):
    """
    Download an export bundle

    Returns the ZIP file containing the export bundle.
    The bundle can be imported to another ZeroDB instance.

    Args:
        project_id: Project UUID
        export_id: Export UUID

    Returns:
        ZIP file download
    """
    try:
        # Build bundle path
        export_dir = os.getenv("EXPORT_DIR", "/tmp/zerodb_exports")
        bundle_path = os.path.join(export_dir, f"export_{export_id}.zip")

        # Check if file exists
        if not os.path.exists(bundle_path):
            raise HTTPException(
                status_code=404,
                detail=f"Export bundle {export_id} not found"
            )

        # Return file
        return FileResponse(
            path=bundle_path,
            media_type="application/zip",
            filename=f"export_{project_id}_{export_id}.zip"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to download export bundle: {str(e)}"
        )


@router.get("/{project_id}/sync/export/preview", response_model=ExportPreview)
async def preview_export(
    project_id: UUID = Path(..., description="Project UUID"),
    export_type: ExportType = Query(
        ExportType.FULL,
        description="Export mode"
    ),
    entity_types: Optional[List[str]] = Query(
        None,
        description="Entity types for selective export"
    ),
    since_timestamp: Optional[datetime] = Query(
        None,
        description="Timestamp for incremental export"
    ),
    db: Session = Depends(get_db)
):
    """
    Preview what would be exported without creating the bundle

    This endpoint performs a dry-run to estimate:
    - Number of entities that would be exported
    - Estimated bundle size
    - Entity types included

    Useful for understanding the scope before creating a large export.

    Args:
        project_id: Project UUID
        export_type: Export mode (full, incremental, selective)
        entity_types: Entity types to include (for selective mode)
        since_timestamp: Timestamp for incremental mode

    Returns:
        Export preview with estimated counts and size
    """
    try:
        # Initialize services
        sync_state_svc = SyncStateService(db)
        export_service.sync_state_service = sync_state_svc

        # Generate preview
        preview = await export_service.preview_export(
            db=db,
            project_id=project_id,
            mode=export_type.value,
            entity_types=entity_types,
            since_timestamp=since_timestamp
        )

        return preview

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate export preview: {str(e)}"
        )
