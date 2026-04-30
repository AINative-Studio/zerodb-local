"""
Tests for Schema Diff Caching Feature (Issue #1249)

Tests schema comparison caching functionality including:
- Saving comparisons to cache
- Retrieving latest comparisons
- Getting breaking changes history
- Cache expiration
- Cloud API schema fetching integration
"""
import pytest
from uuid import UUID, uuid4
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, MagicMock

from services.schema_comparison_service import SchemaComparisonService
from models.schema_comparison import SchemaComparison
from schemas.schema_diff import (
    SchemaDefinition,
    SchemaDiff,
    SchemaChange,
    BreakingChange,
    MigrationPlan,
    MigrationStep,
    ChangeType,
    ChangeSeverity
)


@pytest.fixture
def schema_comparison_service():
    """Create schema comparison service with short TTL for testing"""
    return SchemaComparisonService(cache_ttl_hours=1)


@pytest.fixture
def sample_local_schema():
    """Sample local schema definition"""
    return SchemaDefinition(
        project_id=str(uuid4()),
        tables={
            "users": {
                "name": "users",
                "columns": {
                    "id": {"name": "id", "data_type": "uuid", "nullable": False, "is_primary_key": True},
                    "email": {"name": "email", "data_type": "varchar(255)", "nullable": False}
                },
                "indexes": [],
                "constraints": [],
                "row_count": 100
            }
        },
        vector_collections={},
        buckets={}
    )


@pytest.fixture
def sample_cloud_schema():
    """Sample cloud schema definition with changes"""
    return SchemaDefinition(
        project_id=str(uuid4()),
        tables={
            "users": {
                "name": "users",
                "columns": {
                    "id": {"name": "id", "data_type": "uuid", "nullable": False, "is_primary_key": True},
                    "email": {"name": "email", "data_type": "varchar(255)", "nullable": False},
                    "phone": {"name": "phone", "data_type": "varchar(20)", "nullable": True}
                },
                "indexes": [],
                "constraints": [],
                "row_count": 100
            }
        },
        vector_collections={},
        buckets={}
    )


@pytest.fixture
def sample_schema_diff(sample_local_schema, sample_cloud_schema):
    """Sample schema diff with changes"""
    diff = SchemaDiff(
        local_schema=sample_local_schema,
        cloud_schema=sample_cloud_schema,
        compared_at=datetime.utcnow()
    )

    # Add a change
    diff.added_changes = [
        SchemaChange(
            change_type=ChangeType.COLUMN_ADDED,
            severity=ChangeSeverity.INFO,
            entity_type="table",
            entity_name="users",
            field_name="phone",
            new_value={"data_type": "varchar(20)", "nullable": True},
            description="Added column 'phone' to table 'users'"
        )
    ]
    diff.total_changes = 1
    diff.has_breaking_changes = False

    return diff


@pytest.fixture
def sample_migration_plan():
    """Sample migration plan"""
    return MigrationPlan(
        plan_id="migration_20260227_120000",
        project_id=str(uuid4()),
        steps=[
            MigrationStep(
                step_number=1,
                operation="ALTER TABLE users ADD COLUMN phone VARCHAR(20)",
                description="Add phone column to users table",
                is_reversible=True,
                rollback_operation="ALTER TABLE users DROP COLUMN phone",
                estimated_duration_seconds=0.5,
                affected_entities=["users"]
            )
        ],
        total_steps=1,
        estimated_total_duration_seconds=0.5,
        warnings=[],
        is_safe=True,
        requires_downtime=False,
        breaking_changes_count=0
    )


class TestSchemaComparisonService:
    """Test suite for SchemaComparisonService"""

    def test_save_comparison(
        self,
        db,
        schema_comparison_service,
        sample_local_schema,
        sample_cloud_schema,
        sample_schema_diff,
        sample_migration_plan
    ):
        """Test saving schema comparison to cache"""
        project_id = uuid4()
        summary = "Found 1 non-breaking change"

        # Save comparison
        comparison = schema_comparison_service.save_comparison(
            db=db,
            project_id=project_id,
            local_schema=sample_local_schema,
            cloud_schema=sample_cloud_schema,
            diff=sample_schema_diff,
            migration_plan=sample_migration_plan,
            comparison_summary=summary
        )

        # Assertions
        assert comparison.id is not None
        assert comparison.project_id == project_id
        assert comparison.total_changes == 1
        assert comparison.has_breaking_changes is False
        assert comparison.breaking_changes_count == 0
        assert comparison.comparison_summary == summary
        assert comparison.migration_plan is not None
        assert comparison.expires_at is not None

    def test_get_latest_comparison(
        self,
        db,
        schema_comparison_service,
        sample_local_schema,
        sample_cloud_schema,
        sample_schema_diff,
        sample_migration_plan
    ):
        """Test retrieving latest comparison"""
        project_id = uuid4()

        # Save multiple comparisons
        comparison1 = schema_comparison_service.save_comparison(
            db=db,
            project_id=project_id,
            local_schema=sample_local_schema,
            cloud_schema=sample_cloud_schema,
            diff=sample_schema_diff,
            migration_plan=sample_migration_plan,
            comparison_summary="First comparison"
        )

        comparison2 = schema_comparison_service.save_comparison(
            db=db,
            project_id=project_id,
            local_schema=sample_local_schema,
            cloud_schema=sample_cloud_schema,
            diff=sample_schema_diff,
            migration_plan=sample_migration_plan,
            comparison_summary="Second comparison"
        )

        # Get latest
        latest = schema_comparison_service.get_latest_comparison(
            db=db,
            project_id=project_id
        )

        # Should return the most recent one
        assert latest is not None
        assert latest.comparison_summary == "Second comparison"
        assert latest.id == comparison2.id

    def test_get_latest_comparison_excludes_expired(
        self,
        db,
        schema_comparison_service,
        sample_local_schema,
        sample_cloud_schema,
        sample_schema_diff
    ):
        """Test that latest comparison excludes expired by default"""
        project_id = uuid4()

        # Create expired comparison
        comparison = schema_comparison_service.save_comparison(
            db=db,
            project_id=project_id,
            local_schema=sample_local_schema,
            cloud_schema=sample_cloud_schema,
            diff=sample_schema_diff,
            migration_plan=None,
            comparison_summary="Expired comparison"
        )

        # Manually set expiration to past
        from sqlalchemy import text
        db.execute(
            text("UPDATE schema_comparisons SET expires_at = :exp WHERE id = :id"),
            {"exp": datetime.utcnow() - timedelta(hours=1), "id": str(comparison.id)}
        )
        db.commit()

        # Should not return expired
        latest = schema_comparison_service.get_latest_comparison(
            db=db,
            project_id=project_id,
            include_expired=False
        )
        assert latest is None

        # Should return when including expired
        latest_with_expired = schema_comparison_service.get_latest_comparison(
            db=db,
            project_id=project_id,
            include_expired=True
        )
        assert latest_with_expired is not None
        assert latest_with_expired.id == comparison.id

    def test_get_breaking_changes_history(
        self,
        db,
        schema_comparison_service,
        sample_local_schema,
        sample_cloud_schema
    ):
        """Test retrieving breaking changes history"""
        project_id = uuid4()

        # Create diff with breaking changes
        diff_with_breaking = SchemaDiff(
            local_schema=sample_local_schema,
            cloud_schema=sample_cloud_schema,
            compared_at=datetime.utcnow()
        )

        diff_with_breaking.removed_changes = [
            SchemaChange(
                change_type=ChangeType.COLUMN_REMOVED,
                severity=ChangeSeverity.CRITICAL,
                entity_type="table",
                entity_name="users",
                field_name="legacy_id",
                old_value={"data_type": "integer"},
                description="Removed column 'legacy_id'"
            )
        ]

        diff_with_breaking.breaking_changes = [
            BreakingChange(
                change_type=ChangeType.COLUMN_REMOVED,
                severity=ChangeSeverity.CRITICAL,
                entity_type="table",
                entity_name="users",
                field_name="legacy_id",
                description="Removed column 'legacy_id'",
                impact="Data will be lost",
                mitigation="Export data before migration",
                requires_manual_intervention=True
            )
        ]

        diff_with_breaking.total_changes = 1
        diff_with_breaking.has_breaking_changes = True

        # Save comparison with breaking changes
        schema_comparison_service.save_comparison(
            db=db,
            project_id=project_id,
            local_schema=sample_local_schema,
            cloud_schema=sample_cloud_schema,
            diff=diff_with_breaking,
            migration_plan=None,
            comparison_summary="Critical changes detected"
        )

        # Get breaking changes history
        history = schema_comparison_service.get_breaking_changes_history(
            db=db,
            project_id=project_id,
            limit=10
        )

        # Assertions
        assert len(history) == 1
        assert history[0]["breaking_changes_count"] == 1
        assert history[0]["comparison_summary"] == "Critical changes detected"

    def test_invalidate_expired(
        self,
        db,
        schema_comparison_service,
        sample_local_schema,
        sample_cloud_schema,
        sample_schema_diff
    ):
        """Test invalidating expired comparisons"""
        project_id = uuid4()

        # Create comparison
        comparison = schema_comparison_service.save_comparison(
            db=db,
            project_id=project_id,
            local_schema=sample_local_schema,
            cloud_schema=sample_cloud_schema,
            diff=sample_schema_diff,
            migration_plan=None,
            comparison_summary="Test"
        )

        # Manually expire it
        from sqlalchemy import text
        db.execute(
            text("UPDATE schema_comparisons SET expires_at = :exp WHERE id = :id"),
            {"exp": datetime.utcnow() - timedelta(hours=1), "id": str(comparison.id)}
        )
        db.commit()

        # Invalidate expired
        deleted_count = schema_comparison_service.invalidate_expired(db)

        assert deleted_count == 1

        # Verify it's deleted
        latest = schema_comparison_service.get_comparison_by_id(db, comparison.id)
        assert latest is None


class TestSchemaComparisonAPI:
    """Test suite for schema comparison API endpoints"""

    @pytest.mark.asyncio
    async def test_compare_schemas_with_cloud_api(self, client, db, test_project_id):
        """Test schema comparison with cloud API integration"""
        # Mock CloudAPIClient
        mock_cloud_schema = {
            "tables": {},
            "vector_collections": {},
            "buckets": {},
            "snapshot_timestamp": datetime.utcnow().isoformat()
        }

        with patch('services.cloud_client.CloudAPIClient') as MockCloudClient:
            # Setup mock
            mock_client_instance = AsyncMock()
            mock_client_instance.authenticate = AsyncMock()
            mock_client_instance.get_cloud_schema = AsyncMock(return_value=mock_cloud_schema)
            mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_client_instance.__aexit__ = AsyncMock()

            MockCloudClient.return_value = mock_client_instance

            # Set API key in environment
            import os
            os.environ["ZERODB_API_KEY"] = "test-api-key"

            # Make request without providing cloud_schema
            response = client.post(
                "/v1/schema/compare",
                json={
                    "project_id": test_project_id,
                    "include_migration_plan": True
                }
            )

            # Clean up
            del os.environ["ZERODB_API_KEY"]

            # Verify cloud API was called
            assert mock_client_instance.authenticate.called
            assert mock_client_instance.get_cloud_schema.called

    def test_get_breaking_changes_endpoint(self, client, db, test_project_id):
        """Test retrieving breaking changes from cached comparison"""
        # First create a cached comparison with breaking changes
        from services.schema_comparison_service import SchemaComparisonService
        service = SchemaComparisonService()

        local_schema = SchemaDefinition(
            project_id=test_project_id,
            tables={},
            vector_collections={},
            buckets={}
        )

        cloud_schema = SchemaDefinition(
            project_id=test_project_id,
            tables={},
            vector_collections={},
            buckets={}
        )

        diff = SchemaDiff(
            local_schema=local_schema,
            cloud_schema=cloud_schema,
            compared_at=datetime.utcnow()
        )

        diff.breaking_changes = [
            BreakingChange(
                change_type=ChangeType.TABLE_REMOVED,
                severity=ChangeSeverity.CRITICAL,
                entity_type="table",
                entity_name="old_table",
                description="Table removed",
                impact="Data loss",
                mitigation="Backup data",
                requires_manual_intervention=True
            )
        ]
        diff.has_breaking_changes = True

        service.save_comparison(
            db=db,
            project_id=UUID(test_project_id),
            local_schema=local_schema,
            cloud_schema=cloud_schema,
            diff=diff,
            migration_plan=None,
            comparison_summary="Breaking changes detected"
        )

        # Now fetch breaking changes via API
        response = client.get(f"/v1/schema/breaking-changes/{test_project_id}")

        assert response.status_code == 200
        breaking_changes = response.json()
        assert len(breaking_changes) == 1
        assert breaking_changes[0]["entity_name"] == "old_table"
        assert breaking_changes[0]["requires_manual_intervention"] is True
