"""
Tests for Sync Plan Persistence Feature (Issue #1249)

Tests sync plan storage and retrieval functionality including:
- Saving sync plans
- Retrieving plans by ID
- Plan approval workflow
- Plan execution tracking
- Plan expiration
- Plan status management
"""
import pytest
from uuid import UUID, uuid4
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

from services.sync_plan_service import SyncPlanService
from models.sync_plan import SyncPlan as SyncPlanModel
from schemas.sync_orchestrator import (
    SyncPlan as SyncPlanSchema,
    SyncStep,
    EntityCount,
    SchemaChangeInfo,
    ConflictInfo,
    SyncDirection,
    SyncStepType,
    ConflictResolutionStrategy
)


@pytest.fixture
def sync_plan_service():
    """Create sync plan service with short TTL for testing"""
    return SyncPlanService(plan_ttl_hours=1)


@pytest.fixture
def sample_sync_plan():
    """Sample sync plan for testing"""
    plan_id = uuid4()
    project_id = uuid4()

    return SyncPlanSchema(
        plan_id=plan_id,
        project_id=project_id,
        direction=SyncDirection.PUSH,
        created_at=datetime.utcnow(),
        steps=[
            SyncStep(
                step_number=1,
                step_type=SyncStepType.SCHEMA_VALIDATION,
                description="Validate schema compatibility",
                estimated_duration_seconds=2.0,
                data_count=0
            ),
            SyncStep(
                step_number=2,
                step_type=SyncStepType.EXPORT_CREATION,
                description="Create export bundle",
                estimated_duration_seconds=5.0,
                data_count=100
            ),
            SyncStep(
                step_number=3,
                step_type=SyncStepType.DATA_UPLOAD,
                description="Upload to cloud",
                estimated_duration_seconds=10.0,
                data_count=100
            )
        ],
        entity_counts=EntityCount(
            tables=10,
            table_rows=1000,
            vectors=500,
            memory=50,
            events=200,
            files=25
        ),
        estimated_duration_seconds=17.0,
        estimated_data_size_bytes=1024 * 1024,  # 1MB
        schema_changes=SchemaChangeInfo(
            has_changes=False,
            is_breaking=False,
            changes=[],
            migration_required=False
        ),
        conflicts=ConflictInfo(
            has_conflicts=False,
            conflict_count=0,
            conflicts=[],
            resolution_strategy=ConflictResolutionStrategy.NEWEST_WINS
        ),
        warnings=[],
        requires_approval=False,
        can_rollback=True
    )


@pytest.fixture
def sample_approval_required_plan():
    """Sample sync plan that requires approval"""
    plan_id = uuid4()
    project_id = uuid4()

    return SyncPlanSchema(
        plan_id=plan_id,
        project_id=project_id,
        direction=SyncDirection.PUSH,
        created_at=datetime.utcnow(),
        steps=[
            SyncStep(
                step_number=1,
                step_type=SyncStepType.SCHEMA_VALIDATION,
                description="Validate schema",
                estimated_duration_seconds=2.0,
                data_count=0
            )
        ],
        entity_counts=EntityCount(),
        estimated_duration_seconds=2.0,
        estimated_data_size_bytes=0,
        schema_changes=SchemaChangeInfo(
            has_changes=True,
            is_breaking=True,
            changes=["Breaking change detected"],
            migration_required=True
        ),
        conflicts=ConflictInfo(
            has_conflicts=False,
            conflict_count=0,
            conflicts=[],
            resolution_strategy=ConflictResolutionStrategy.NEWEST_WINS
        ),
        warnings=["Breaking schema changes require approval"],
        requires_approval=True,
        can_rollback=True
    )


class TestSyncPlanService:
    """Test suite for SyncPlanService"""

    def test_save_plan(self, db, sync_plan_service, sample_sync_plan):
        """Test saving sync plan to database"""
        # Save plan
        plan_model = sync_plan_service.save_plan(db, sample_sync_plan)

        # Assertions
        assert plan_model.id is not None
        assert plan_model.plan_id == sample_sync_plan.plan_id
        assert plan_model.project_id == sample_sync_plan.project_id
        assert plan_model.direction == sample_sync_plan.direction.value
        assert plan_model.status == 'pending'
        assert plan_model.total_steps == 3
        assert len(plan_model.steps) == 3
        assert plan_model.requires_approval is False
        assert plan_model.expires_at is not None

    def test_get_plan_by_id(self, db, sync_plan_service, sample_sync_plan):
        """Test retrieving plan by ID"""
        # Save plan
        saved_plan = sync_plan_service.save_plan(db, sample_sync_plan)

        # Retrieve plan
        retrieved_plan = sync_plan_service.get_plan_by_id(
            db=db,
            plan_id=saved_plan.plan_id,
            project_id=saved_plan.project_id
        )

        # Assertions
        assert retrieved_plan is not None
        assert retrieved_plan.plan_id == saved_plan.plan_id
        assert retrieved_plan.project_id == saved_plan.project_id
        assert retrieved_plan.total_steps == 3

    def test_get_plan_by_id_wrong_project(self, db, sync_plan_service, sample_sync_plan):
        """Test that plan retrieval fails with wrong project ID"""
        # Save plan
        saved_plan = sync_plan_service.save_plan(db, sample_sync_plan)

        # Try to retrieve with wrong project ID
        wrong_project_id = uuid4()
        retrieved_plan = sync_plan_service.get_plan_by_id(
            db=db,
            plan_id=saved_plan.plan_id,
            project_id=wrong_project_id
        )

        # Should not find plan
        assert retrieved_plan is None

    def test_get_plans_for_project(self, db, sync_plan_service, sample_sync_plan):
        """Test retrieving all plans for a project"""
        # Save multiple plans
        plan1 = sync_plan_service.save_plan(db, sample_sync_plan)

        sample_sync_plan.plan_id = uuid4()  # Change plan ID
        plan2 = sync_plan_service.save_plan(db, sample_sync_plan)

        # Get plans for project
        plans = sync_plan_service.get_plans_for_project(
            db=db,
            project_id=sample_sync_plan.project_id,
            limit=50
        )

        # Should return both plans
        assert len(plans) == 2
        plan_ids = [p.plan_id for p in plans]
        assert plan1.plan_id in plan_ids
        assert plan2.plan_id in plan_ids

    def test_approve_plan(self, db, sync_plan_service, sample_approval_required_plan):
        """Test approving a sync plan"""
        # Save plan that requires approval
        saved_plan = sync_plan_service.save_plan(db, sample_approval_required_plan)

        # Approve plan
        approved_plan = sync_plan_service.approve_plan(
            db=db,
            plan_id=saved_plan.plan_id,
            approved_by="test_user"
        )

        # Assertions
        assert approved_plan is not None
        assert approved_plan.status == 'approved'
        assert approved_plan.approved_by == "test_user"
        assert approved_plan.approved_at is not None

    def test_mark_executing(self, db, sync_plan_service, sample_sync_plan):
        """Test marking plan as executing"""
        # Save plan
        saved_plan = sync_plan_service.save_plan(db, sample_sync_plan)

        # Mark as executing
        executing_plan = sync_plan_service.mark_executing(db, saved_plan.plan_id)

        # Assertions
        assert executing_plan is not None
        assert executing_plan.status == 'executing'
        assert executing_plan.executed_at is not None

    def test_mark_executing_approval_required(
        self,
        db,
        sync_plan_service,
        sample_approval_required_plan
    ):
        """Test that plan requiring approval cannot be executed without approval"""
        # Save plan that requires approval
        saved_plan = sync_plan_service.save_plan(db, sample_approval_required_plan)

        # Try to mark as executing without approval
        result = sync_plan_service.mark_executing(db, saved_plan.plan_id)

        # Should fail because approval required
        assert result is None or not result.is_executable()

        # Approve first
        sync_plan_service.approve_plan(db, saved_plan.plan_id, "test_user")

        # Now should succeed
        executing_plan = sync_plan_service.mark_executing(db, saved_plan.plan_id)
        assert executing_plan is not None
        assert executing_plan.status == 'executing'

    def test_mark_completed(self, db, sync_plan_service, sample_sync_plan):
        """Test marking plan as completed"""
        # Save and execute plan
        saved_plan = sync_plan_service.save_plan(db, sample_sync_plan)
        sync_plan_service.mark_executing(db, saved_plan.plan_id)

        # Mark as completed
        sync_result_id = uuid4()
        completed_plan = sync_plan_service.mark_completed(
            db=db,
            plan_id=saved_plan.plan_id,
            sync_result_id=sync_result_id
        )

        # Assertions
        assert completed_plan is not None
        assert completed_plan.status == 'completed'
        assert completed_plan.completed_at is not None
        assert completed_plan.sync_result_id == sync_result_id

    def test_mark_failed(self, db, sync_plan_service, sample_sync_plan):
        """Test marking plan as failed"""
        # Save and execute plan
        saved_plan = sync_plan_service.save_plan(db, sample_sync_plan)
        sync_plan_service.mark_executing(db, saved_plan.plan_id)

        # Mark as failed
        failed_plan = sync_plan_service.mark_failed(db, saved_plan.plan_id)

        # Assertions
        assert failed_plan is not None
        assert failed_plan.status == 'failed'
        assert failed_plan.completed_at is not None

    def test_plan_expiration(self, db, sync_plan_service, sample_sync_plan):
        """Test plan expiration detection"""
        # Save plan
        saved_plan = sync_plan_service.save_plan(db, sample_sync_plan)

        # Initially not expired
        assert not saved_plan.is_expired()

        # Manually expire plan
        from sqlalchemy import text
        db.execute(
            text("UPDATE sync_plans SET expires_at = :exp WHERE plan_id = :id"),
            {"exp": datetime.utcnow() - timedelta(hours=1), "id": str(saved_plan.plan_id)}
        )
        db.commit()

        # Retrieve again
        expired_plan = sync_plan_service.get_plan_by_id(db, saved_plan.plan_id)

        # Should be marked as expired
        assert expired_plan is not None
        assert expired_plan.status == 'expired'

    def test_invalidate_expired_plans(self, db, sync_plan_service, sample_sync_plan):
        """Test marking expired plans"""
        # Save plan
        saved_plan = sync_plan_service.save_plan(db, sample_sync_plan)

        # Manually set expiration to past
        from sqlalchemy import text
        db.execute(
            text("UPDATE sync_plans SET expires_at = :exp WHERE plan_id = :id"),
            {"exp": datetime.utcnow() - timedelta(hours=1), "id": str(saved_plan.plan_id)}
        )
        db.commit()

        # Invalidate expired plans
        expired_count = sync_plan_service.invalidate_expired(db)

        assert expired_count == 1

        # Verify status changed to expired
        plan = sync_plan_service.get_plan_by_id(db, saved_plan.plan_id)
        assert plan.status == 'expired'

    def test_delete_plan(self, db, sync_plan_service, sample_sync_plan):
        """Test deleting a sync plan"""
        # Save plan
        saved_plan = sync_plan_service.save_plan(db, sample_sync_plan)

        # Delete plan
        deleted = sync_plan_service.delete_plan(db, saved_plan.plan_id)

        assert deleted is True

        # Verify plan is gone
        plan = sync_plan_service.get_plan_by_id(db, saved_plan.plan_id)
        assert plan is None

    def test_cleanup_old_plans(self, db, sync_plan_service, sample_sync_plan):
        """Test cleaning up old completed plans"""
        # Save and complete a plan
        saved_plan = sync_plan_service.save_plan(db, sample_sync_plan)
        sync_plan_service.mark_executing(db, saved_plan.plan_id)
        sync_plan_service.mark_completed(db, saved_plan.plan_id, uuid4())

        # Manually set creation date to old
        from sqlalchemy import text
        db.execute(
            text("UPDATE sync_plans SET created_at = :created WHERE plan_id = :id"),
            {"created": datetime.utcnow() - timedelta(days=31), "id": str(saved_plan.plan_id)}
        )
        db.commit()

        # Cleanup old plans
        deleted_count = sync_plan_service.cleanup_old_plans(db, days_old=30)

        assert deleted_count == 1

        # Verify plan is deleted
        plan = sync_plan_service.get_plan_by_id(db, saved_plan.plan_id)
        assert plan is None


class TestSyncPlanAPI:
    """Test suite for sync plan API endpoints"""

    @pytest.mark.asyncio
    async def test_plan_sync_saves_to_database(self, client, db, test_project_id):
        """Test that planning a sync saves plan to database"""
        # Make request to plan sync
        response = client.post(
            f"/v1/projects/{test_project_id}/sync/plan",
            json={
                "direction": "push",
                "entity_types": ["tables", "vectors"],
                "conflict_strategy": "newest_wins",
                "include_schema": False
            }
        )

        # Should succeed
        assert response.status_code == 200
        plan_data = response.json()

        # Verify plan was saved to database
        service = SyncPlanService()
        plan_id = UUID(plan_data["plan_id"])
        saved_plan = service.get_plan_by_id(db, plan_id, UUID(test_project_id))

        assert saved_plan is not None
        assert saved_plan.status == 'pending'

    @pytest.mark.asyncio
    async def test_execute_sync_retrieves_plan_from_database(self, client, db, test_project_id):
        """Test that executing sync retrieves plan from database"""
        # First create a plan
        service = SyncPlanService()

        plan = SyncPlanSchema(
            plan_id=uuid4(),
            project_id=UUID(test_project_id),
            direction=SyncDirection.PUSH,
            created_at=datetime.utcnow(),
            steps=[
                SyncStep(
                    step_number=1,
                    step_type=SyncStepType.SCHEMA_VALIDATION,
                    description="Validate",
                    estimated_duration_seconds=1.0,
                    data_count=0
                )
            ],
            entity_counts=EntityCount(),
            estimated_duration_seconds=1.0,
            estimated_data_size_bytes=0,
            schema_changes=SchemaChangeInfo(
                has_changes=False,
                is_breaking=False,
                changes=[],
                migration_required=False
            ),
            conflicts=ConflictInfo(
                has_conflicts=False,
                conflict_count=0,
                conflicts=[],
                resolution_strategy=ConflictResolutionStrategy.NEWEST_WINS
            ),
            warnings=[],
            requires_approval=False,
            can_rollback=True
        )

        saved_plan = service.save_plan(db, plan)

        # Execute the plan
        response = client.post(
            f"/v1/projects/{test_project_id}/sync/execute",
            json={
                "plan_id": str(saved_plan.plan_id),
                "approved": False,
                "conflict_resolutions": {}
            }
        )

        # Verify plan was retrieved and executed
        assert response.status_code == 200

        # Check plan status was updated
        updated_plan = service.get_plan_by_id(db, saved_plan.plan_id, UUID(test_project_id))
        assert updated_plan.status in ['executing', 'completed', 'failed']

    @pytest.mark.asyncio
    async def test_validate_sync_plan_retrieves_from_database(self, client, db, test_project_id):
        """Test that validating sync plan retrieves from database"""
        # Create a plan
        service = SyncPlanService()

        plan = SyncPlanSchema(
            plan_id=uuid4(),
            project_id=UUID(test_project_id),
            direction=SyncDirection.PUSH,
            created_at=datetime.utcnow(),
            steps=[],
            entity_counts=EntityCount(),
            estimated_duration_seconds=0.0,
            estimated_data_size_bytes=0,
            schema_changes=SchemaChangeInfo(
                has_changes=False,
                is_breaking=False,
                changes=[],
                migration_required=False
            ),
            conflicts=ConflictInfo(
                has_conflicts=False,
                conflict_count=0,
                conflicts=[],
                resolution_strategy=ConflictResolutionStrategy.NEWEST_WINS
            ),
            warnings=[],
            requires_approval=False,
            can_rollback=True
        )

        saved_plan = service.save_plan(db, plan)

        # Validate the plan
        response = client.post(
            f"/v1/projects/{test_project_id}/sync/validate",
            params={"plan_id": str(saved_plan.plan_id)}
        )

        # Should succeed
        assert response.status_code == 200
        validation = response.json()
        assert "is_valid" in validation
