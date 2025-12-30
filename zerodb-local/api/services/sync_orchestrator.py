"""
Sync Orchestrator Service
Core coordination layer for sync operations between local and cloud
"""
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import text
import logging
import json

from schemas.sync_orchestrator import (
    SyncPlan,
    SyncResult,
    ValidationResult,
    RollbackResult,
    SyncStatusResponse,
    SyncStep,
    SyncStepResult,
    EntityCount,
    SchemaChangeInfo,
    ConflictInfo,
    SyncWarning,
    SyncDirection,
    SyncStepType,
    SyncStatus,
    EntityType,
    OperationType,
    ConflictResolutionStrategy,
)
from services.sync_state_service import SyncStateService
from services.cdc_service import CDCService
from services.schema_diff_service import SchemaDiffService
from services.sync_history_service import SyncHistoryService
from services.pull_sync_service import PullSyncService

logger = logging.getLogger(__name__)


class SyncOrchestrator:
    """
    Orchestrates sync operations between local and cloud

    Responsibilities:
    - Generate sync plans (what needs to sync and in what order)
    - Execute sync operations (push/pull)
    - Validate sync plans before execution
    - Handle rollbacks on failure
    - Coordinate all sync-related services
    """

    def __init__(
        self,
        db: Session,
        sync_state_service: Optional[SyncStateService] = None,
        cdc_service: Optional[CDCService] = None,
        schema_diff_service: Optional[SchemaDiffService] = None,
        sync_history_service: Optional[SyncHistoryService] = None,
        pull_sync_service: Optional[PullSyncService] = None
    ):
        """
        Initialize sync orchestrator

        Args:
            db: Database session
            sync_state_service: Service for sync state management
            cdc_service: Service for change data capture
            schema_diff_service: Service for schema comparison
            sync_history_service: Service for sync history tracking
            pull_sync_service: Service for pull sync operations
        """
        self.db = db
        self.sync_state_service = sync_state_service or SyncStateService(db)
        self.cdc_service = cdc_service or CDCService()
        self.schema_diff_service = schema_diff_service or SchemaDiffService()
        self.sync_history_service = sync_history_service or SyncHistoryService(db)
        self.pull_sync_service = pull_sync_service or PullSyncService(db)

    async def plan_sync(
        self,
        project_id: UUID,
        direction: SyncDirection = SyncDirection.PUSH,
        entity_types: Optional[List[EntityType]] = None,
        conflict_strategy: ConflictResolutionStrategy = ConflictResolutionStrategy.NEWEST_WINS,
        include_schema: bool = True
    ) -> SyncPlan:
        """
        Generate a sync plan

        Args:
            project_id: Project UUID
            direction: Sync direction (push/pull)
            entity_types: Specific entity types to sync (None = all)
            conflict_strategy: Strategy for conflict resolution
            include_schema: Whether to include schema sync

        Returns:
            SyncPlan with all steps and metadata
        """
        logger.info(f"Planning {direction} sync for project {project_id}")

        plan_id = uuid4()
        created_at = datetime.utcnow()

        # Get sync state for all entity types
        entity_types_to_sync = entity_types or [
            EntityType.TABLES,
            EntityType.VECTORS,
            EntityType.MEMORY,
            EntityType.EVENTS,
            EntityType.FILES
        ]

        # Analyze what needs to sync
        entity_counts = await self._count_entities_to_sync(
            project_id, direction, entity_types_to_sync
        )

        # Check for schema changes
        schema_changes = await self._analyze_schema_changes(
            project_id, include_schema
        ) if include_schema else SchemaChangeInfo(
            has_changes=False,
            is_breaking=False,
            changes=[],
            migration_required=False
        )

        # Detect conflicts
        conflicts = await self._detect_conflicts(
            project_id, direction, conflict_strategy
        )

        # Generate sync steps
        steps = await self._generate_sync_steps(
            direction, entity_types_to_sync, entity_counts, schema_changes
        )

        # Calculate estimates
        estimated_duration = sum(
            step.estimated_duration_seconds or 0 for step in steps
        )
        estimated_data_size = await self._estimate_data_size(
            entity_counts
        )

        # Generate warnings
        warnings = self._generate_warnings(
            schema_changes, conflicts, entity_counts, estimated_data_size
        )

        # Determine if approval required
        requires_approval = (
            schema_changes.is_breaking or
            conflicts.has_conflicts or
            estimated_data_size > 100 * 1024 * 1024  # > 100MB
        )

        plan = SyncPlan(
            plan_id=plan_id,
            project_id=project_id,
            direction=direction,
            created_at=created_at,
            steps=steps,
            entity_counts=entity_counts,
            estimated_duration_seconds=estimated_duration,
            estimated_data_size_bytes=estimated_data_size,
            schema_changes=schema_changes,
            conflicts=conflicts,
            warnings=warnings,
            requires_approval=requires_approval,
            can_rollback=True
        )

        logger.info(
            f"Generated sync plan {plan_id}: "
            f"{len(steps)} steps, "
            f"~{estimated_duration:.1f}s, "
            f"~{estimated_data_size / (1024*1024):.1f}MB"
        )

        return plan

    async def execute_sync(
        self,
        project_id: UUID,
        sync_plan: SyncPlan,
        approved: bool = False,
        conflict_resolutions: Optional[Dict[str, str]] = None
    ) -> SyncResult:
        """
        Execute a sync plan

        Args:
            project_id: Project UUID
            sync_plan: Plan to execute
            approved: Whether manual approval provided
            conflict_resolutions: Manual conflict resolutions

        Returns:
            SyncResult with execution details
        """
        logger.info(f"Executing sync {sync_plan.plan_id} for project {project_id}")

        # Validate approval if required
        if sync_plan.requires_approval and not approved:
            raise ValueError(
                "Sync requires manual approval. Set approved=True to proceed."
            )

        sync_id = uuid4()
        started_at = datetime.utcnow()
        snapshot_id = await self._create_snapshot(project_id)

        # Create sync history entry
        from schemas.sync_history import SyncDirection as HistoryDirection, SyncMode
        history_direction = {
            SyncDirection.PUSH: HistoryDirection.PUSH,
            SyncDirection.PULL: HistoryDirection.PULL
        }.get(sync_plan.direction, HistoryDirection.PUSH)

        history_entry = self.sync_history_service.create_history_entry(
            project_id=project_id,
            sync_id=sync_id,
            direction=history_direction,
            mode=SyncMode.INCREMENTAL,  # Can be enhanced based on sync_plan
            snapshot_id=snapshot_id
        )

        # Update status to running
        from schemas.sync_history import SyncStatus as HistoryStatus
        self.sync_history_service.update_history(
            sync_id=sync_id,
            status=HistoryStatus.RUNNING
        )

        step_results: List[SyncStepResult] = []
        total_records_synced = 0
        total_bytes_transferred = 0
        errors: List[str] = []
        records_by_entity: Dict[str, int] = {}

        try:
            # Execute each step in order
            for step in sync_plan.steps:
                step_result = await self._execute_step(
                    project_id,
                    step,
                    sync_plan.direction,
                    conflict_resolutions
                )
                step_results.append(step_result)

                if step_result.status == SyncStatus.FAILED:
                    errors.append(
                        f"Step {step.step_number} failed: {step_result.error_message}"
                    )
                    # Rollback on failure
                    logger.error(f"Step {step.step_number} failed, initiating rollback")
                    await self._rollback_to_snapshot(project_id, snapshot_id)

                    # Update sync history with failure
                    self.sync_history_service.update_history(
                        sync_id=sync_id,
                        status=HistoryStatus.ROLLED_BACK,
                        completed_at=datetime.utcnow(),
                        records_synced=records_by_entity,
                        bytes_transferred=total_bytes_transferred,
                        error_message=step_result.error_message
                    )

                    return SyncResult(
                        sync_id=sync_id,
                        project_id=project_id,
                        plan_id=sync_plan.plan_id,
                        direction=sync_plan.direction,
                        status=SyncStatus.FAILED,
                        started_at=started_at,
                        completed_at=datetime.utcnow(),
                        duration_seconds=(datetime.utcnow() - started_at).total_seconds(),
                        steps_completed=step_results,
                        total_steps=len(sync_plan.steps),
                        successful_steps=len([r for r in step_results if r.status == SyncStatus.COMPLETED]),
                        failed_steps=len([r for r in step_results if r.status == SyncStatus.FAILED]),
                        records_synced=total_records_synced,
                        bytes_transferred=total_bytes_transferred,
                        errors=errors,
                        rollback_available=False,  # Already rolled back
                        snapshot_id=snapshot_id
                    )

                total_records_synced += step_result.records_processed

            # All steps succeeded
            completed_at = datetime.utcnow()
            duration = (completed_at - started_at).total_seconds()

            # Update sync history with success
            self.sync_history_service.update_history(
                sync_id=sync_id,
                status=HistoryStatus.COMPLETED,
                completed_at=completed_at,
                records_synced=records_by_entity,
                bytes_transferred=total_bytes_transferred
            )

            result = SyncResult(
                sync_id=sync_id,
                project_id=project_id,
                plan_id=sync_plan.plan_id,
                direction=sync_plan.direction,
                status=SyncStatus.COMPLETED,
                started_at=started_at,
                completed_at=completed_at,
                duration_seconds=duration,
                steps_completed=step_results,
                total_steps=len(sync_plan.steps),
                successful_steps=len(step_results),
                failed_steps=0,
                records_synced=total_records_synced,
                bytes_transferred=total_bytes_transferred,
                errors=[],
                rollback_available=True,
                snapshot_id=snapshot_id
            )

            logger.info(
                f"Sync {sync_id} completed successfully: "
                f"{total_records_synced} records in {duration:.1f}s"
            )

            return result

        except Exception as e:
            logger.exception(f"Sync {sync_id} failed with exception")
            errors.append(f"Unexpected error: {str(e)}")

            # Rollback on exception
            await self._rollback_to_snapshot(project_id, snapshot_id)

            # Update sync history with exception failure
            self.sync_history_service.update_history(
                sync_id=sync_id,
                status=HistoryStatus.FAILED,
                completed_at=datetime.utcnow(),
                records_synced=records_by_entity,
                bytes_transferred=total_bytes_transferred,
                error_message=str(e),
                error_stack=str(e.__traceback__) if hasattr(e, '__traceback__') else None
            )

            return SyncResult(
                sync_id=sync_id,
                project_id=project_id,
                plan_id=sync_plan.plan_id,
                direction=sync_plan.direction,
                status=SyncStatus.FAILED,
                started_at=started_at,
                completed_at=datetime.utcnow(),
                duration_seconds=(datetime.utcnow() - started_at).total_seconds(),
                steps_completed=step_results,
                total_steps=len(sync_plan.steps),
                successful_steps=len([r for r in step_results if r.status == SyncStatus.COMPLETED]),
                failed_steps=len([r for r in step_results if r.status == SyncStatus.FAILED]) + 1,
                records_synced=total_records_synced,
                bytes_transferred=total_bytes_transferred,
                errors=errors,
                rollback_available=False,
                snapshot_id=snapshot_id
            )

    async def validate_sync_plan(
        self,
        sync_plan: SyncPlan
    ) -> ValidationResult:
        """
        Validate a sync plan before execution

        Args:
            sync_plan: Plan to validate

        Returns:
            ValidationResult with validation details
        """
        logger.info(f"Validating sync plan {sync_plan.plan_id}")

        errors: List[str] = []
        warnings: List[SyncWarning] = []
        recommendations: List[str] = []

        # Validate steps are in correct order
        expected_step_number = 1
        for step in sync_plan.steps:
            if step.step_number != expected_step_number:
                errors.append(
                    f"Step {step.step_number} out of order, "
                    f"expected {expected_step_number}"
                )
            expected_step_number += 1

        # Validate schema changes are addressed
        if sync_plan.schema_changes.is_breaking:
            if not any(
                step.step_type == SyncStepType.SCHEMA_VALIDATION
                for step in sync_plan.steps
            ):
                errors.append(
                    "Breaking schema changes detected but no schema validation step"
                )

        # Check for conflicts
        if sync_plan.conflicts.has_conflicts:
            warnings.append(SyncWarning(
                severity="high",
                message=f"{sync_plan.conflicts.conflict_count} conflicts detected",
                category="conflicts"
            ))
            recommendations.append(
                "Review conflicts before execution or use conflict resolution strategy"
            )

        # Check data volume
        if sync_plan.estimated_data_size_bytes > 1024 * 1024 * 1024:  # 1GB
            warnings.append(SyncWarning(
                severity="medium",
                message="Large data transfer (>1GB), may take significant time",
                category="performance"
            ))
            recommendations.append(
                "Consider selective sync or schedule during off-peak hours"
            )

        # Validate entity counts
        total_entities = (
            sync_plan.entity_counts.tables +
            sync_plan.entity_counts.vectors +
            sync_plan.entity_counts.memory +
            sync_plan.entity_counts.events +
            sync_plan.entity_counts.files
        )

        if total_entities == 0:
            warnings.append(SyncWarning(
                severity="low",
                message="No entities to sync",
                category="data"
            ))

        is_valid = len(errors) == 0

        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            recommendations=recommendations
        )

    async def rollback_sync(
        self,
        project_id: UUID,
        sync_id: UUID
    ) -> RollbackResult:
        """
        Rollback a completed sync

        Args:
            project_id: Project UUID
            sync_id: Sync to rollback

        Returns:
            RollbackResult with rollback details
        """
        logger.info(f"Rolling back sync {sync_id} for project {project_id}")

        try:
            # Get sync record to find snapshot
            sync_record = await self._get_sync_record(sync_id)

            if not sync_record:
                raise ValueError(f"Sync {sync_id} not found")

            snapshot_id = sync_record.get("snapshot_id")
            if not snapshot_id:
                raise ValueError(f"No snapshot available for sync {sync_id}")

            # Restore from snapshot
            restored_state = await self._rollback_to_snapshot(
                project_id, UUID(snapshot_id)
            )

            return RollbackResult(
                success=True,
                sync_id=sync_id,
                snapshot_id=UUID(snapshot_id),
                restored_at=datetime.utcnow(),
                restored_state=restored_state,
                errors=[]
            )

        except Exception as e:
            logger.exception(f"Rollback failed for sync {sync_id}")
            return RollbackResult(
                success=False,
                sync_id=sync_id,
                snapshot_id=UUID("00000000-0000-0000-0000-000000000000"),
                restored_at=datetime.utcnow(),
                restored_state={},
                errors=[str(e)]
            )

    async def get_sync_status(
        self,
        project_id: UUID
    ) -> SyncStatusResponse:
        """
        Get current sync status for a project

        Args:
            project_id: Project UUID

        Returns:
            SyncStatusResponse with current status
        """
        logger.info(f"Getting sync status for project {project_id}")

        # Get sync states for all entity types
        entity_sync_states = {}

        for entity_type in ["tables", "vectors", "memory", "events", "files"]:
            sync_state = self.sync_state_service.get_sync_state(
                project_id, entity_type
            )

            if sync_state:
                entity_sync_states[entity_type] = {
                    "last_sync_at": sync_state.last_sync_at.isoformat() if sync_state.last_sync_at else None,
                    "sync_strategy": sync_state.sync_strategy,
                    "sync_direction": sync_state.sync_direction,
                    "watermark": sync_state.watermark
                }

        # Get pending changes count
        pending_changes = self.cdc_service.get_unsynced_changes(
            self.db, project_id
        )

        # Check for in-progress sync
        current_sync = await self._get_current_sync(project_id)

        # Get last successful sync
        last_sync = await self._get_last_successful_sync(project_id)

        return SyncStatusResponse(
            project_id=project_id,
            last_sync_at=last_sync.get("completed_at") if last_sync else None,
            last_sync_direction=SyncDirection(last_sync.get("direction")) if last_sync else None,
            sync_in_progress=current_sync is not None,
            current_sync_id=UUID(current_sync["sync_id"]) if current_sync else None,
            pending_changes_count=len(pending_changes),
            entity_sync_states=entity_sync_states
        )

    # Private helper methods

    async def _count_entities_to_sync(
        self,
        project_id: UUID,
        direction: SyncDirection,
        entity_types: List[EntityType]
    ) -> EntityCount:
        """Count entities that need to be synced"""
        # Get last sync time from sync state
        counts = EntityCount()

        for entity_type in entity_types:
            sync_state = self.sync_state_service.get_sync_state(
                project_id, entity_type.value
            )

            since = sync_state.last_sync_at if sync_state else None

            if direction == SyncDirection.PUSH:
                # Count local changes
                changes = self.cdc_service.get_unsynced_changes(
                    self.db, project_id, entity_type.value
                )

                if entity_type == EntityType.TABLES:
                    counts.tables = len([c for c in changes if c["operation"] == "CREATE"])
                    counts.table_rows = len(changes)
                elif entity_type == EntityType.VECTORS:
                    counts.vectors = len(changes)
                elif entity_type == EntityType.MEMORY:
                    counts.memory = len(changes)
                elif entity_type == EntityType.EVENTS:
                    counts.events = len(changes)
                elif entity_type == EntityType.FILES:
                    counts.files = len(changes)

        return counts

    async def _analyze_schema_changes(
        self,
        project_id: UUID,
        include_schema: bool
    ) -> SchemaChangeInfo:
        """Analyze schema changes between local and cloud"""
        if not include_schema:
            return SchemaChangeInfo(
                has_changes=False,
                is_breaking=False,
                changes=[],
                migration_required=False
            )

        # Get local schema
        local_schema = await self.schema_diff_service.get_local_schema(
            self.db, project_id
        )

        # TODO: Get cloud schema from CloudAPIClient
        # For now, assume no schema changes
        return SchemaChangeInfo(
            has_changes=False,
            is_breaking=False,
            changes=[],
            migration_required=False
        )

    async def _detect_conflicts(
        self,
        project_id: UUID,
        direction: SyncDirection,
        strategy: ConflictResolutionStrategy
    ) -> ConflictInfo:
        """Detect conflicts between local and cloud"""
        # TODO: Implement conflict detection by comparing timestamps
        # For now, assume no conflicts
        return ConflictInfo(
            has_conflicts=False,
            conflict_count=0,
            conflicts=[],
            resolution_strategy=strategy
        )

    async def _generate_sync_steps(
        self,
        direction: SyncDirection,
        entity_types: List[EntityType],
        entity_counts: EntityCount,
        schema_changes: SchemaChangeInfo
    ) -> List[SyncStep]:
        """Generate ordered list of sync steps"""
        steps: List[SyncStep] = []
        step_num = 1

        # Step 1: Schema validation
        if schema_changes.has_changes:
            steps.append(SyncStep(
                step_number=step_num,
                step_type=SyncStepType.SCHEMA_VALIDATION,
                description="Validate schema compatibility",
                estimated_duration_seconds=2.0
            ))
            step_num += 1

        if direction == SyncDirection.PUSH:
            # Step 2: Create export bundle
            steps.append(SyncStep(
                step_number=step_num,
                step_type=SyncStepType.EXPORT_CREATION,
                data_count=entity_counts.tables + entity_counts.vectors + entity_counts.memory,
                description="Create export bundle from local data",
                estimated_duration_seconds=5.0
            ))
            step_num += 1

            # Step 3: Upload to cloud
            steps.append(SyncStep(
                step_number=step_num,
                step_type=SyncStepType.DATA_UPLOAD,
                description="Upload bundle to cloud",
                estimated_duration_seconds=10.0
            ))
            step_num += 1

        elif direction == SyncDirection.PULL:
            # Step 2: Download from cloud
            steps.append(SyncStep(
                step_number=step_num,
                step_type=SyncStepType.DATA_DOWNLOAD,
                description="Download bundle from cloud",
                estimated_duration_seconds=10.0
            ))
            step_num += 1

            # Step 3: Import data
            steps.append(SyncStep(
                step_number=step_num,
                step_type=SyncStepType.IMPORT_DATA,
                description="Import data to local database",
                estimated_duration_seconds=5.0
            ))
            step_num += 1

        # Final steps: Update watermarks and mark synced
        steps.append(SyncStep(
            step_number=step_num,
            step_type=SyncStepType.UPDATE_WATERMARKS,
            description="Update sync watermarks",
            estimated_duration_seconds=1.0
        ))
        step_num += 1

        steps.append(SyncStep(
            step_number=step_num,
            step_type=SyncStepType.MARK_SYNCED,
            description="Mark changes as synced",
            estimated_duration_seconds=1.0
        ))

        return steps

    async def _estimate_data_size(
        self,
        entity_counts: EntityCount
    ) -> int:
        """Estimate data size in bytes"""
        # Rough estimates per entity type
        size = 0
        size += entity_counts.table_rows * 1024  # 1KB per row
        size += entity_counts.vectors * 6 * 1024  # 6KB per vector (1536 dims * 4 bytes)
        size += entity_counts.memory * 512  # 512B per memory record
        size += entity_counts.events * 256  # 256B per event
        size += entity_counts.files * 128  # 128B per file metadata

        return size

    def _generate_warnings(
        self,
        schema_changes: SchemaChangeInfo,
        conflicts: ConflictInfo,
        entity_counts: EntityCount,
        estimated_data_size: int
    ) -> List[SyncWarning]:
        """Generate warnings for sync plan"""
        warnings: List[SyncWarning] = []

        if schema_changes.is_breaking:
            warnings.append(SyncWarning(
                severity="high",
                message="Breaking schema changes detected - may cause data loss",
                category="schema"
            ))

        if conflicts.has_conflicts:
            warnings.append(SyncWarning(
                severity="high",
                message=f"{conflicts.conflict_count} conflicts require resolution",
                category="conflicts"
            ))

        if estimated_data_size > 100 * 1024 * 1024:  # >100MB
            warnings.append(SyncWarning(
                severity="medium",
                message="Large data transfer - ensure stable network connection",
                category="performance"
            ))

        total_entities = (
            entity_counts.tables + entity_counts.vectors +
            entity_counts.memory + entity_counts.events + entity_counts.files
        )

        if total_entities == 0:
            warnings.append(SyncWarning(
                severity="low",
                message="No entities to sync",
                category="data"
            ))

        return warnings

    async def _execute_step(
        self,
        project_id: UUID,
        step: SyncStep,
        direction: SyncDirection,
        conflict_resolutions: Optional[Dict[str, str]]
    ) -> SyncStepResult:
        """Execute a single sync step"""
        logger.info(f"Executing step {step.step_number}: {step.step_type}")

        started_at = datetime.utcnow()

        try:
            # TODO: Implement actual step execution
            # For now, simulate success
            import asyncio
            await asyncio.sleep(step.estimated_duration_seconds or 1.0)

            completed_at = datetime.utcnow()
            duration = (completed_at - started_at).total_seconds()

            return SyncStepResult(
                step_number=step.step_number,
                step_type=step.step_type,
                status=SyncStatus.COMPLETED,
                started_at=started_at,
                completed_at=completed_at,
                duration_seconds=duration,
                records_processed=step.data_count
            )

        except Exception as e:
            logger.exception(f"Step {step.step_number} failed")
            return SyncStepResult(
                step_number=step.step_number,
                step_type=step.step_type,
                status=SyncStatus.FAILED,
                started_at=started_at,
                completed_at=datetime.utcnow(),
                duration_seconds=(datetime.utcnow() - started_at).total_seconds(),
                error_message=str(e),
                records_processed=0
            )

    async def _create_snapshot(
        self,
        project_id: UUID
    ) -> UUID:
        """Create snapshot for rollback"""
        snapshot_id = uuid4()

        # TODO: Implement actual snapshot creation
        logger.info(f"Created snapshot {snapshot_id} for project {project_id}")

        return snapshot_id

    async def _rollback_to_snapshot(
        self,
        project_id: UUID,
        snapshot_id: UUID
    ) -> Dict[str, Any]:
        """Rollback to a previous snapshot"""
        logger.info(f"Rolling back project {project_id} to snapshot {snapshot_id}")

        # TODO: Implement actual rollback
        return {
            "project_id": str(project_id),
            "snapshot_id": str(snapshot_id),
            "restored_at": datetime.utcnow().isoformat()
        }

    async def _get_sync_record(
        self,
        sync_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """Get sync record by ID"""
        # TODO: Implement sync record retrieval from database
        return None

    async def _get_current_sync(
        self,
        project_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """Get currently running sync for project"""
        # TODO: Implement current sync check
        return None

    async def _get_last_successful_sync(
        self,
        project_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """Get last successful sync for project"""
        # TODO: Implement last sync retrieval
        return None
