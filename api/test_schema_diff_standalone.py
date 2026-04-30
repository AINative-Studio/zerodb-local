"""
Standalone Schema Diff Service Tests
Tests for schema comparison and migration planning - Story #431
Can be run without external dependencies
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from uuid import uuid4
import copy

# Import directly to bypass __init__.py
from services.schema_diff_service import SchemaDiffService
from schemas import schema_diff as schema_diff_module

SchemaDefinition = schema_diff_module.SchemaDefinition
TableDefinition = schema_diff_module.TableDefinition
ColumnDefinition = schema_diff_module.ColumnDefinition
IndexDefinition = schema_diff_module.IndexDefinition
VectorCollectionDefinition = schema_diff_module.VectorCollectionDefinition
BucketDefinition = schema_diff_module.BucketDefinition
ChangeType = schema_diff_module.ChangeType
ChangeSeverity = schema_diff_module.ChangeSeverity


def create_sample_local_schema():
    """Sample local schema for testing"""
    return SchemaDefinition(
        project_id=str(uuid4()),
        tables={
            "users": TableDefinition(
                name="users",
                columns={
                    "id": ColumnDefinition(
                        name="id",
                        data_type="uuid",
                        nullable=False,
                        is_primary_key=True
                    ),
                    "email": ColumnDefinition(
                        name="email",
                        data_type="varchar(255)",
                        nullable=False
                    ),
                    "name": ColumnDefinition(
                        name="name",
                        data_type="varchar(100)",
                        nullable=True
                    )
                },
                indexes=[
                    IndexDefinition(
                        name="idx_users_email",
                        columns=["email"],
                        unique=True
                    )
                ],
                row_count=100
            ),
            "products": TableDefinition(
                name="products",
                columns={
                    "id": ColumnDefinition(
                        name="id",
                        data_type="uuid",
                        nullable=False,
                        is_primary_key=True
                    ),
                    "name": ColumnDefinition(
                        name="name",
                        data_type="varchar(255)",
                        nullable=False
                    ),
                    "price": ColumnDefinition(
                        name="price",
                        data_type="decimal(10,2)",
                        nullable=False
                    )
                },
                row_count=50
            )
        },
        vector_collections={
            "embeddings": VectorCollectionDefinition(
                name="embeddings",
                vector_dimension=1536,
                distance_metric="cosine",
                vector_count=1000
            )
        },
        buckets={
            "uploads": BucketDefinition(
                name="uploads",
                policy="private",
                object_count=25
            )
        }
    )


def test_compare_identical_schemas():
    """Test comparison of identical schemas returns no changes"""
    print("\n[TEST] Comparing identical schemas...")
    service = SchemaDiffService()
    local_schema = create_sample_local_schema()
    cloud_schema = copy.deepcopy(local_schema)

    diff = service.compare_schemas(local_schema, cloud_schema)

    assert diff.total_changes == 0, f"Expected 0 changes, got {diff.total_changes}"
    assert len(diff.added_changes) == 0, f"Expected no additions, got {len(diff.added_changes)}"
    assert len(diff.removed_changes) == 0, f"Expected no removals, got {len(diff.removed_changes)}"
    assert len(diff.modified_changes) == 0, f"Expected no modifications, got {len(diff.modified_changes)}"
    assert not diff.has_breaking_changes, "Expected no breaking changes"
    assert len(diff.breaking_changes) == 0, f"Expected 0 breaking changes, got {len(diff.breaking_changes)}"

    print("✅ PASSED: Identical schemas comparison")


def test_detect_added_columns():
    """Test detection of new columns added to tables"""
    print("\n[TEST] Detecting added columns...")
    service = SchemaDiffService()
    local_schema = create_sample_local_schema()
    cloud_schema = copy.deepcopy(local_schema)

    # Add new column to users table
    cloud_schema.tables["users"].columns["phone_number"] = ColumnDefinition(
        name="phone_number",
        data_type="varchar(20)",
        nullable=True
    )

    diff = service.compare_schemas(local_schema, cloud_schema)

    added_column_changes = [
        c for c in diff.added_changes
        if c.change_type == ChangeType.COLUMN_ADDED
    ]
    assert len(added_column_changes) == 1, f"Expected 1 column addition, got {len(added_column_changes)}"
    assert added_column_changes[0].field_name == "phone_number", f"Expected 'phone_number', got {added_column_changes[0].field_name}"
    assert added_column_changes[0].entity_name == "users", f"Expected 'users', got {added_column_changes[0].entity_name}"
    assert added_column_changes[0].severity == ChangeSeverity.INFO, f"Expected INFO severity, got {added_column_changes[0].severity}"

    print("✅ PASSED: Column addition detection")


def test_detect_added_tables():
    """Test detection of new tables"""
    print("\n[TEST] Detecting added tables...")
    service = SchemaDiffService()
    local_schema = create_sample_local_schema()
    cloud_schema = copy.deepcopy(local_schema)

    # Add new table
    cloud_schema.tables["orders"] = TableDefinition(
        name="orders",
        columns={
            "id": ColumnDefinition(
                name="id",
                data_type="uuid",
                nullable=False,
                is_primary_key=True
            ),
            "total": ColumnDefinition(
                name="total",
                data_type="decimal(10,2)",
                nullable=False
            )
        },
        row_count=0
    )

    diff = service.compare_schemas(local_schema, cloud_schema)

    added_table_changes = [
        c for c in diff.added_changes
        if c.change_type == ChangeType.TABLE_ADDED
    ]
    assert len(added_table_changes) == 1, f"Expected 1 table addition, got {len(added_table_changes)}"
    assert added_table_changes[0].entity_name == "orders", f"Expected 'orders', got {added_table_changes[0].entity_name}"
    assert added_table_changes[0].severity == ChangeSeverity.INFO

    print("✅ PASSED: Table addition detection")


def test_detect_removed_columns():
    """Test detection of removed columns (breaking change)"""
    print("\n[TEST] Detecting removed columns...")
    service = SchemaDiffService()
    local_schema = create_sample_local_schema()
    cloud_schema = copy.deepcopy(local_schema)

    # Remove column from users table
    del cloud_schema.tables["users"].columns["name"]

    diff = service.compare_schemas(local_schema, cloud_schema)

    removed_column_changes = [
        c for c in diff.removed_changes
        if c.change_type == ChangeType.COLUMN_REMOVED
    ]
    assert len(removed_column_changes) == 1, f"Expected 1 column removal, got {len(removed_column_changes)}"
    assert removed_column_changes[0].field_name == "name"
    assert removed_column_changes[0].severity == ChangeSeverity.CRITICAL

    print("✅ PASSED: Column removal detection")


def test_detect_column_type_change():
    """Test detection of column type changes (breaking change)"""
    print("\n[TEST] Detecting column type changes...")
    service = SchemaDiffService()
    local_schema = create_sample_local_schema()
    cloud_schema = copy.deepcopy(local_schema)

    # Change email column type
    cloud_schema.tables["users"].columns["email"].data_type = "text"

    diff = service.compare_schemas(local_schema, cloud_schema)

    type_changes = [
        c for c in diff.modified_changes
        if c.change_type == ChangeType.COLUMN_TYPE_CHANGED
    ]
    assert len(type_changes) == 1
    assert type_changes[0].field_name == "email"
    assert type_changes[0].old_value == "varchar(255)"
    assert type_changes[0].new_value == "text"
    assert type_changes[0].severity == ChangeSeverity.CRITICAL

    print("✅ PASSED: Column type change detection")


def test_breaking_changes_detection():
    """Test that removals create breaking changes"""
    print("\n[TEST] Detecting breaking changes...")
    service = SchemaDiffService()
    local_schema = create_sample_local_schema()
    cloud_schema = copy.deepcopy(local_schema)

    # Remove column and table
    del cloud_schema.tables["users"].columns["name"]
    del cloud_schema.tables["products"]

    diff = service.compare_schemas(local_schema, cloud_schema)

    assert diff.has_breaking_changes, "Expected breaking changes to be detected"
    assert len(diff.breaking_changes) > 0, "Expected at least one breaking change"

    # Verify breaking changes have impact and mitigation
    for breaking_change in diff.breaking_changes:
        assert breaking_change.impact, "Breaking change should have impact description"
        assert breaking_change.mitigation, "Breaking change should have mitigation"
        assert breaking_change.severity == ChangeSeverity.CRITICAL

    print("✅ PASSED: Breaking change detection")


def test_migration_plan_generation():
    """Test migration plan generation for schema additions"""
    print("\n[TEST] Generating migration plan...")
    service = SchemaDiffService()
    local_schema = create_sample_local_schema()
    cloud_schema = copy.deepcopy(local_schema)

    # Add new column
    cloud_schema.tables["users"].columns["phone_number"] = ColumnDefinition(
        name="phone_number",
        data_type="varchar(20)",
        nullable=True
    )

    diff = service.compare_schemas(local_schema, cloud_schema)
    plan = service.generate_migration_plan(diff, uuid4())

    assert plan.total_steps > 0, "Expected migration steps to be generated"
    assert plan.is_safe, "Additions should be safe"
    assert not plan.requires_downtime, "Additions should not require downtime"
    assert plan.breaking_changes_count == 0

    # Verify steps have required fields
    for step in plan.steps:
        assert step.operation, "Step should have operation"
        assert step.description, "Step should have description"
        assert step.estimated_duration_seconds is not None, "Step should have duration estimate"

    print("✅ PASSED: Migration plan generation")
    print(f"   Generated {plan.total_steps} migration steps")
    print(f"   Estimated duration: {plan.estimated_total_duration_seconds}s")


def test_migration_plan_with_breaking_changes():
    """Test migration plan flags breaking changes correctly"""
    print("\n[TEST] Migration plan with breaking changes...")
    service = SchemaDiffService()
    local_schema = create_sample_local_schema()
    cloud_schema = copy.deepcopy(local_schema)

    # Remove column and table (breaking changes)
    del cloud_schema.tables["users"].columns["name"]
    del cloud_schema.tables["products"]

    diff = service.compare_schemas(local_schema, cloud_schema)
    plan = service.generate_migration_plan(diff, uuid4())

    assert not plan.is_safe, "Plan should not be safe with breaking changes"
    assert plan.requires_downtime, "Plan should require downtime with breaking changes"
    assert plan.breaking_changes_count > 0, "Should have breaking changes count"
    assert len(plan.warnings) > 0, "Should have warnings"

    # Verify warnings mention breaking changes
    warning_text = " ".join(plan.warnings).lower()
    assert "breaking" in warning_text, "Warnings should mention breaking changes"

    print("✅ PASSED: Migration plan with breaking changes")
    print(f"   Breaking changes: {plan.breaking_changes_count}")
    print(f"   Warnings: {len(plan.warnings)}")


if __name__ == "__main__":
    print("=" * 60)
    print("Schema Diff Service Tests - Story #431")
    print("=" * 60)

    tests = [
        test_compare_identical_schemas,
        test_detect_added_columns,
        test_detect_added_tables,
        test_detect_removed_columns,
        test_detect_column_type_change,
        test_breaking_changes_detection,
        test_migration_plan_generation,
        test_migration_plan_with_breaking_changes
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"❌ FAILED: {test.__name__}")
            print(f"   {str(e)}")
            failed += 1
        except Exception as e:
            print(f"❌ ERROR in {test.__name__}: {str(e)}")
            failed += 1

    print("\n" + "=" * 60)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("=" * 60)

    if failed == 0:
        print("✅ ALL TESTS PASSED")
        exit(0)
    else:
        print("❌ SOME TESTS FAILED")
        exit(1)
