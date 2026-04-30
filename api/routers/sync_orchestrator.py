"""
Sync Orchestrator Router
API endpoints for sync orchestration
"""
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from schemas.sync_orchestrator import (
    SyncPlan,
    SyncPlanRequest,
    SyncResult,
    SyncExecuteRequest,
    ValidationResult,
    RollbackResult,
    SyncStatusResponse,
    SyncDirection,
    EntityType,
    ConflictResolutionStrategy,
)
from services.sync_orchestrator import SyncOrchestrator
from services.sync_state_service import SyncStateService
from services.cdc_service import CDCService
from services.schema_diff_service import SchemaDiffService
from services.sync_plan_service import SyncPlanService

router = APIRouter(prefix="/v1/projects", tags=["sync-orchestrator"])


def get_sync_orchestrator(db: Session = Depends(get_db)) -> SyncOrchestrator:
    """Dependency to get sync orchestrator instance"""
    return SyncOrchestrator(
        db=db,
        sync_state_service=SyncStateService(db),
        cdc_service=CDCService(),
        schema_diff_service=SchemaDiffService()
    )


def get_sync_plan_service() -> SyncPlanService:
    """Dependency to get sync plan service instance"""
    return SyncPlanService()


@router.post(
    "/{project_id}/sync/plan",
    response_model=SyncPlan,
    status_code=status.HTTP_200_OK,
    summary="Generate sync plan",
    description="""
    Generate a sync plan for a project.

    The plan includes:
    - Ordered list of sync steps
    - Entity counts to sync
    - Schema change analysis
    - Conflict detection
    - Time and size estimates
    - Warnings and recommendations

    Use this to preview what will happen before executing sync.
    """
)
async def plan_sync(
    project_id: UUID,
    request: SyncPlanRequest,
    orchestrator: SyncOrchestrator = Depends(get_sync_orchestrator),
    plan_service: SyncPlanService = Depends(get_sync_plan_service),
    db: Session = Depends(get_db)
) -> SyncPlan:
    """
    Generate sync plan

    Args:
        project_id: Project UUID
        request: Sync plan request parameters
        orchestrator: Sync orchestrator instance

    Returns:
        Complete sync plan

    Raises:
        HTTPException: If plan generation fails
    """
    try:
        plan = await orchestrator.plan_sync(
            project_id=project_id,
            direction=request.direction,
            entity_types=request.entity_types,
            conflict_strategy=request.conflict_strategy,
            include_schema=request.include_schema
        )

        # Save plan to database for later execution
        try:
            plan_service.save_plan(db, plan)
        except Exception as save_error:
            # Log but don't fail - plan can still be used immediately
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to save sync plan: {save_error}")

        return plan

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate sync plan: {str(e)}"
        )


@router.post(
    "/{project_id}/sync/execute",
    response_model=SyncResult,
    status_code=status.HTTP_200_OK,
    summary="Execute sync plan",
    description="""
    Execute a sync plan.

    This will:
    1. Validate the plan
    2. Create a snapshot for rollback
    3. Execute each step in order
    4. Update sync state on success
    5. Rollback on failure

    If the plan requires approval, you must set approved=True.
    """
)
async def execute_sync(
    project_id: UUID,
    request: SyncExecuteRequest,
    orchestrator: SyncOrchestrator = Depends(get_sync_orchestrator),
    plan_service: SyncPlanService = Depends(get_sync_plan_service),
    db: Session = Depends(get_db)
) -> SyncResult:
    """
    Execute sync plan

    Args:
        project_id: Project UUID
        request: Sync execution request
        orchestrator: Sync orchestrator instance

    Returns:
        Sync execution result

    Raises:
        HTTPException: If execution fails or plan not found
    """
    try:
        # Retrieve the plan from database
        plan_model = plan_service.get_plan_by_id(
            db=db,
            plan_id=request.plan_id,
            project_id=project_id
        )

        if not plan_model:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Sync plan {request.plan_id} not found"
            )

        # Check if plan can be executed
        if not plan_model.is_executable():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Sync plan cannot be executed: status={plan_model.status}, "
                       f"expired={plan_model.is_expired()}, "
                       f"requires_approval={plan_model.requires_approval}, "
                       f"approved={plan_model.approved_at is not None}"
            )

        # Convert database model to schema
        from schemas.sync_orchestrator import (
            SyncPlan, SyncStep, EntityCount, SchemaChangeInfo, ConflictInfo
        )

        sync_plan = SyncPlan(
            plan_id=plan_model.plan_id,
            project_id=plan_model.project_id,
            direction=SyncDirection(plan_model.direction),
            created_at=plan_model.created_at,
            steps=[SyncStep(**step) for step in plan_model.steps],
            entity_counts=EntityCount(**plan_model.entity_counts),
            estimated_duration_seconds=plan_model.estimated_duration_seconds,
            estimated_data_size_bytes=plan_model.estimated_data_size_bytes,
            schema_changes=SchemaChangeInfo(**plan_model.schema_changes),
            conflicts=ConflictInfo(**plan_model.conflicts),
            warnings=plan_model.warnings,
            requires_approval=plan_model.requires_approval,
            can_rollback=plan_model.can_rollback
        )

        # Mark plan as executing
        plan_service.mark_executing(db, request.plan_id)

        # Execute sync
        result = await orchestrator.execute_sync(
            project_id=project_id,
            sync_plan=sync_plan,
            approved=request.approved,
            conflict_resolutions=request.conflict_resolutions
        )

        # Update plan status based on result
        if result.status == SyncStatus.COMPLETED:
            plan_service.mark_completed(db, request.plan_id, result.sync_id)
        else:
            plan_service.mark_failed(db, request.plan_id)

        return result

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Sync execution failed: {str(e)}"
        )


@router.post(
    "/{project_id}/sync/validate",
    response_model=ValidationResult,
    status_code=status.HTTP_200_OK,
    summary="Validate sync plan",
    description="""
    Validate a sync plan before execution.

    Checks:
    - Step ordering
    - Schema compatibility
    - Conflict resolution
    - Data volume limits
    - Resource availability

    Returns validation result with errors, warnings, and recommendations.
    """
)
async def validate_sync_plan(
    project_id: UUID,
    plan_id: UUID,
    orchestrator: SyncOrchestrator = Depends(get_sync_orchestrator),
    plan_service: SyncPlanService = Depends(get_sync_plan_service),
    db: Session = Depends(get_db)
) -> ValidationResult:
    """
    Validate sync plan

    Args:
        project_id: Project UUID
        plan_id: Plan ID to validate
        orchestrator: Sync orchestrator instance

    Returns:
        Validation result

    Raises:
        HTTPException: If plan not found or validation fails
    """
    try:
        # Retrieve plan from database
        plan_model = plan_service.get_plan_by_id(
            db=db,
            plan_id=plan_id,
            project_id=project_id
        )

        if not plan_model:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Sync plan {plan_id} not found"
            )

        # Convert database model to schema
        from schemas.sync_orchestrator import (
            SyncPlan, SyncStep, EntityCount, SchemaChangeInfo, ConflictInfo
        )

        sync_plan = SyncPlan(
            plan_id=plan_model.plan_id,
            project_id=plan_model.project_id,
            direction=SyncDirection(plan_model.direction),
            created_at=plan_model.created_at,
            steps=[SyncStep(**step) for step in plan_model.steps],
            entity_counts=EntityCount(**plan_model.entity_counts),
            estimated_duration_seconds=plan_model.estimated_duration_seconds,
            estimated_data_size_bytes=plan_model.estimated_data_size_bytes,
            schema_changes=SchemaChangeInfo(**plan_model.schema_changes),
            conflicts=ConflictInfo(**plan_model.conflicts),
            warnings=plan_model.warnings,
            requires_approval=plan_model.requires_approval,
            can_rollback=plan_model.can_rollback
        )

        result = await orchestrator.validate_sync_plan(sync_plan)

        return result

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Validation failed: {str(e)}"
        )


@router.post(
    "/{project_id}/sync/rollback/{sync_id}",
    response_model=RollbackResult,
    status_code=status.HTTP_200_OK,
    summary="Rollback sync",
    description="""
    Rollback a completed or failed sync.

    This will:
    1. Retrieve the sync snapshot
    2. Restore database state
    3. Revert sync watermarks
    4. Mark changes as unsynced

    Only syncs with available snapshots can be rolled back.
    """
)
async def rollback_sync(
    project_id: UUID,
    sync_id: UUID,
    orchestrator: SyncOrchestrator = Depends(get_sync_orchestrator)
) -> RollbackResult:
    """
    Rollback sync

    Args:
        project_id: Project UUID
        sync_id: Sync ID to rollback
        orchestrator: Sync orchestrator instance

    Returns:
        Rollback result

    Raises:
        HTTPException: If sync not found or rollback fails
    """
    try:
        result = await orchestrator.rollback_sync(
            project_id=project_id,
            sync_id=sync_id
        )

        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Rollback failed: {', '.join(result.errors)}"
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Rollback failed: {str(e)}"
        )


@router.get(
    "/{project_id}/sync/status",
    response_model=SyncStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Get sync status",
    description="""
    Get current sync status for a project.

    Returns:
    - Last sync timestamp
    - Sync in progress indicator
    - Pending changes count
    - Entity-specific sync states
    - Watermark information
    """
)
async def get_sync_status(
    project_id: UUID,
    orchestrator: SyncOrchestrator = Depends(get_sync_orchestrator)
) -> SyncStatusResponse:
    """
    Get sync status

    Args:
        project_id: Project UUID
        orchestrator: Sync orchestrator instance

    Returns:
        Sync status

    Raises:
        HTTPException: If status retrieval fails
    """
    try:
        status_response = await orchestrator.get_sync_status(project_id)

        return status_response

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get sync status: {str(e)}"
        )
