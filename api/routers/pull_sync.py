"""
Pull Sync Router
API endpoints for cloud → local sync operations
"""
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlalchemy.orm import Session

from schemas.pull_sync import (
    PullRequest,
    PullResult,
    PullPreview,
    BundleImportRequest,
    BundleImportResult
)
from services.pull_sync_service import PullSyncService
from services.import_service import ImportService
from db.session import get_db
from errors import (
    CloudAPINotFoundError,
    CloudAPIAuthenticationError,
    ValidationError
)

router = APIRouter(prefix="/v1/projects", tags=["pull-sync"])


def get_api_key(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
) -> str:
    """Extract API key from header"""
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required in X-API-Key header"
        )
    return x_api_key


@router.post("/{project_id}/sync/pull", response_model=PullResult)
async def pull_from_cloud(
    project_id: UUID,
    request: PullRequest,
    api_key: str = Depends(get_api_key),
    db: Session = Depends(get_db)
) -> PullResult:
    """
    Pull data from cloud to local database

    Workflow:
    1. Authenticate with cloud
    2. Download latest bundle
    3. Validate schema compatibility
    4. Detect conflicts
    5. Import data
    6. Update watermarks

    Args:
        project_id: Project UUID (from path)
        request: Pull request with options
        api_key: Cloud API key (from header)
        db: Database session

    Returns:
        PullResult with import details and status

    Raises:
        HTTPException 401: Authentication failed
        HTTPException 404: Bundle not found
        HTTPException 422: Validation failed
        HTTPException 500: Import failed

    Example:
        POST /v1/projects/{project_id}/sync/pull
        Headers: X-API-Key: your-api-key
        Body: {
            "project_id": "a1b2c3d4-...",
            "entity_types": ["vectors", "tables"],
            "conflict_action": "overwrite",
            "validate_schema": true,
            "dry_run": false
        }
    """
    try:
        # Override project_id in request with path param
        request.project_id = project_id

        # Create service
        pull_service = PullSyncService(db)

        # Execute pull
        result = await pull_service.pull_from_cloud(request, api_key)

        return result

    except CloudAPIAuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
    except CloudAPINotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Pull sync failed: {str(e)}"
        )


@router.get("/{project_id}/sync/pull/preview", response_model=PullPreview)
async def preview_pull_changes(
    project_id: UUID,
    api_key: str = Depends(get_api_key),
    db: Session = Depends(get_db)
) -> PullPreview:
    """
    Preview what would be pulled from cloud without applying changes

    Useful for:
    - Checking what has changed in cloud
    - Estimating sync duration
    - Detecting schema conflicts before pulling
    - Reviewing breaking changes

    Args:
        project_id: Project UUID
        api_key: Cloud API key (from header)
        db: Database session

    Returns:
        PullPreview with estimated changes and validation

    Raises:
        HTTPException 401: Authentication failed
        HTTPException 404: Bundle not found
        HTTPException 500: Preview failed

    Example:
        GET /v1/projects/{project_id}/sync/pull/preview
        Headers: X-API-Key: your-api-key

        Response: {
            "project_id": "a1b2c3d4-...",
            "cloud_bundle_id": "b1c2d3e4-...",
            "estimated_counts": {
                "tables_created": 2,
                "table_rows_inserted": 500,
                "vectors_upserted": 250,
                "total_imported": 752
            },
            "validation": {
                "is_valid": true,
                "schema_compatible": true,
                "breaking_changes": []
            },
            "safe_to_pull": true
        }
    """
    try:
        pull_service = PullSyncService(db)
        preview = await pull_service.preview_pull(project_id, api_key)
        return preview

    except CloudAPIAuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
    except CloudAPINotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Preview failed: {str(e)}"
        )


@router.post("/{project_id}/sync/pull/apply", response_model=BundleImportResult)
async def apply_downloaded_bundle(
    project_id: UUID,
    request: BundleImportRequest,
    db: Session = Depends(get_db)
) -> BundleImportResult:
    """
    Apply a previously downloaded bundle to local database

    This endpoint allows you to:
    1. Download a bundle separately
    2. Review the contents
    3. Apply it with specific conflict resolution strategy

    Useful for:
    - Manual bundle review before import
    - Testing import with different conflict strategies
    - Importing saved bundles offline

    Args:
        project_id: Project UUID
        request: Bundle import request with data and options
        db: Database session

    Returns:
        BundleImportResult with counts and conflicts

    Raises:
        HTTPException 422: Validation failed
        HTTPException 500: Import failed

    Example:
        POST /v1/projects/{project_id}/sync/pull/apply
        Body: {
            "project_id": "a1b2c3d4-...",
            "bundle_data": { ... },
            "conflict_action": "merge",
            "validate_first": true,
            "create_snapshot": true
        }
    """
    try:
        # Override project_id with path param
        request.project_id = project_id

        # Create import service
        import_service = ImportService(db)

        # Import bundle
        result = await import_service.import_bundle(request)

        return result

    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Bundle import failed: {str(e)}"
        )
