"""
Schema Diff Router
Handles schema comparison and migration planning
"""
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

# Import schemas
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from schemas.schema_diff import (
    SchemaCompareRequest,
    SchemaCompareResponse,
    SchemaDiff,
    BreakingChange,
    MigrationPlan,
    SchemaDefinition
)

# Import authentication from local auth module
from auth import get_current_user as get_current_user_flexible, User

# Import services
from services.database_service import database_service
from services.schema_diff_service import SchemaDiffService
from services.qdrant_service import QdrantService
from services.minio_service import MinIOService
from services.cloud_client import CloudAPIClient
from services.schema_comparison_service import SchemaComparisonService


router = APIRouter()

# Initialize services
qdrant_service = QdrantService()
minio_service = MinIOService()
schema_diff_service = SchemaDiffService(
    qdrant_service=qdrant_service,
    minio_service=minio_service
)
schema_comparison_service = SchemaComparisonService()


@router.post("/compare", response_model=SchemaCompareResponse)
async def compare_schemas(
    request: SchemaCompareRequest,
    current_user: User = Depends(get_current_user_flexible),
    db: Session = Depends(database_service.get_db)
):
    """
    Compare local and cloud schemas

    **Authentication:** Required

    **Parameters:**
    - project_id: Project UUID to compare
    - cloud_schema: Optional cloud schema (if not provided, fetch from cloud API)
    - include_migration_plan: Whether to generate migration plan (default: true)

    **Returns:**
    - Schema comparison with differences
    - Optional migration plan
    - Summary of changes

    **Example:**
    ```json
    {
        "project_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        "include_migration_plan": true
    }
    ```

    **Response:**
    - total_changes: Number of schema differences
    - has_breaking_changes: Whether critical changes detected
    - migration_plan: Steps to apply changes (if requested)
    """
    try:
        project_uuid = UUID(request.project_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid project_id format. Must be a valid UUID."
        )

    # Verify project exists and user has access
    from sqlalchemy import text
    project_query = text("""
        SELECT id FROM projects
        WHERE id = :project_id
        AND user_id = :user_id
        AND deleted_at IS NULL
    """)

    project = db.execute(
        project_query,
        {"project_id": str(project_uuid), "user_id": str(current_user.id)}
    ).first()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {request.project_id} not found or access denied"
        )

    # Get local schema
    try:
        local_schema = await schema_diff_service.get_local_schema(db, project_uuid)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve local schema: {str(e)}"
        )

    # Get or parse cloud schema
    if request.cloud_schema:
        cloud_schema = request.cloud_schema
    else:
        # Fetch from cloud API
        import os
        api_key = os.getenv("ZERODB_API_KEY")
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="cloud_schema not provided and ZERODB_API_KEY not configured. "
                       "Either provide cloud_schema or set ZERODB_API_KEY environment variable."
            )

        try:
            async with CloudAPIClient() as cloud_client:
                # Authenticate with cloud API
                await cloud_client.authenticate(api_key)

                # Fetch cloud schema
                cloud_schema_data = await cloud_client.get_cloud_schema(request.project_id)

                # Parse into SchemaDefinition
                cloud_schema = schema_diff_service.parse_cloud_schema(cloud_schema_data)

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to fetch cloud schema: {str(e)}"
            )

    # Compare schemas
    try:
        diff = schema_diff_service.compare_schemas(local_schema, cloud_schema)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to compare schemas: {str(e)}"
        )

    # Generate migration plan if requested
    migration_plan = None
    if request.include_migration_plan and diff.total_changes > 0:
        try:
            migration_plan = schema_diff_service.generate_migration_plan(diff, project_uuid)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate migration plan: {str(e)}"
            )

    # Generate summary
    summary = _generate_comparison_summary(diff, migration_plan)

    # Save comparison to cache
    try:
        schema_comparison_service.save_comparison(
            db=db,
            project_id=project_uuid,
            local_schema=local_schema,
            cloud_schema=cloud_schema,
            diff=diff,
            migration_plan=migration_plan,
            comparison_summary=summary
        )
    except Exception as e:
        # Log error but don't fail the request
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Failed to cache schema comparison: {e}")

    return SchemaCompareResponse(
        project_id=request.project_id,
        diff=diff,
        migration_plan=migration_plan,
        comparison_summary=summary
    )


@router.get("/breaking-changes/{project_id}", response_model=List[BreakingChange])
async def get_breaking_changes(
    project_id: str,
    current_user: User = Depends(get_current_user_flexible),
    db: Session = Depends(database_service.get_db)
):
    """
    Get breaking changes for a project schema comparison

    **Authentication:** Required

    **Parameters:**
    - project_id: Project UUID

    **Returns:**
    - List of breaking changes with impact and mitigation

    **Note:** This endpoint requires a previous schema comparison to exist.
    Currently returns empty list if no comparison cached.
    """
    try:
        project_uuid = UUID(project_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid project_id format. Must be a valid UUID."
        )

    # Verify project exists and user has access
    from sqlalchemy import text
    project_query = text("""
        SELECT id FROM projects
        WHERE id = :project_id
        AND user_id = :user_id
        AND deleted_at IS NULL
    """)

    project = db.execute(
        project_query,
        {"project_id": str(project_uuid), "user_id": str(current_user.id)}
    ).first()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found or access denied"
        )

    # Get latest schema comparison from cache
    try:
        latest_comparison = schema_comparison_service.get_latest_comparison(
            db=db,
            project_id=project_uuid,
            include_expired=False
        )

        if not latest_comparison or not latest_comparison.has_breaking_changes:
            return []

        # Extract breaking changes from cached diff
        from schemas.schema_diff import BreakingChange
        diff_result = latest_comparison.diff_result

        if not diff_result or 'breaking_changes' not in diff_result:
            return []

        # Convert dict to BreakingChange objects
        breaking_changes = [
            BreakingChange(**bc) for bc in diff_result['breaking_changes']
        ]

        return breaking_changes

    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to retrieve breaking changes: {e}")
        return []


@router.post("/migration-plan", response_model=MigrationPlan)
async def generate_migration_plan(
    request: SchemaCompareRequest,
    current_user: User = Depends(get_current_user_flexible),
    db: Session = Depends(database_service.get_db)
):
    """
    Generate migration plan for schema changes

    **Authentication:** Required

    **Parameters:**
    - project_id: Project UUID
    - cloud_schema: Cloud schema to migrate to

    **Returns:**
    - Migration plan with ordered steps
    - Estimated duration
    - Warnings for breaking changes

    **Example Response:**
    ```json
    {
        "plan_id": "migration_20251229_120000",
        "total_steps": 5,
        "is_safe": true,
        "requires_downtime": false,
        "breaking_changes_count": 0,
        "steps": [
            {
                "step_number": 1,
                "operation": "ALTER TABLE users ADD COLUMN phone VARCHAR(20)",
                "description": "Add phone column",
                "is_reversible": true,
                "estimated_duration_seconds": 0.5
            }
        ]
    }
    ```
    """
    try:
        project_uuid = UUID(request.project_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid project_id format. Must be a valid UUID."
        )

    # Verify project exists and user has access
    from sqlalchemy import text
    project_query = text("""
        SELECT id FROM projects
        WHERE id = :project_id
        AND user_id = :user_id
        AND deleted_at IS NULL
    """)

    project = db.execute(
        project_query,
        {"project_id": str(project_uuid), "user_id": str(current_user.id)}
    ).first()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {request.project_id} not found or access denied"
        )

    # Get local schema
    try:
        local_schema = await schema_diff_service.get_local_schema(db, project_uuid)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve local schema: {str(e)}"
        )

    # Validate cloud schema provided
    if not request.cloud_schema:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="cloud_schema is required to generate migration plan"
        )

    # Compare schemas
    try:
        diff = schema_diff_service.compare_schemas(local_schema, request.cloud_schema)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to compare schemas: {str(e)}"
        )

    # Generate migration plan
    try:
        migration_plan = schema_diff_service.generate_migration_plan(diff, project_uuid)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate migration plan: {str(e)}"
        )

    return migration_plan


def _generate_comparison_summary(diff: SchemaDiff, migration_plan: Optional[MigrationPlan]) -> str:
    """
    Generate human-readable summary of schema comparison

    Args:
        diff: Schema diff
        migration_plan: Optional migration plan

    Returns:
        Summary string
    """
    if diff.total_changes == 0:
        return "Schemas are identical. No migration needed."

    summary_parts = []

    # Change counts
    summary_parts.append(f"Found {diff.total_changes} schema differences:")
    if diff.added_changes:
        summary_parts.append(f"  - {len(diff.added_changes)} additions")
    if diff.removed_changes:
        summary_parts.append(f"  - {len(diff.removed_changes)} removals")
    if diff.modified_changes:
        summary_parts.append(f"  - {len(diff.modified_changes)} modifications")

    # Breaking changes
    if diff.has_breaking_changes:
        summary_parts.append(f"⚠️  {len(diff.breaking_changes)} BREAKING CHANGES detected!")
        summary_parts.append("Migration requires careful review and manual intervention.")
    else:
        summary_parts.append("✅ All changes are non-breaking and safe to apply.")

    # Migration plan summary
    if migration_plan:
        summary_parts.append(f"\nMigration plan generated with {migration_plan.total_steps} steps.")
        summary_parts.append(f"Estimated duration: {migration_plan.estimated_total_duration_seconds:.1f} seconds")

        if migration_plan.warnings:
            summary_parts.append(f"⚠️  {len(migration_plan.warnings)} warnings:")
            for warning in migration_plan.warnings[:3]:  # Show first 3
                summary_parts.append(f"  - {warning}")

    return "\n".join(summary_parts)
