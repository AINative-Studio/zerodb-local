"""
Schema Diff Service Tests Runner
Tests for schema comparison and migration planning - Story #431
"""
import sys
import importlib.util
from uuid import uuid4
import copy

# Load modules directly to bypass __init__.py imports
spec = importlib.util.spec_from_file_location('schema_diff_service', 'services/schema_diff_service.py')
schema_diff_service_module = importlib.util.module_from_spec(spec)
sys.modules['schema_diff_service'] = schema_diff_service_module
spec.loader.exec_module(schema_diff_service_module)

spec2 = importlib.util.spec_from_file_location('schema_diff', 'schemas/schema_diff.py')
schema_diff_module = importlib.util.module_from_spec(spec2)
sys.modules['schema_diff'] = schema_diff_module
spec2.loader.exec_module(schema_diff_module)

SchemaDiffService = schema_diff_service_module.SchemaDiffService
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
                    "id": ColumnDefinition(name="id", data_type="uuid", nullable=False, is_primary_key=True),
                    "email": ColumnDefinition(name="email", data_type="varchar(255)", nullable=False),
                    "name": ColumnDefinition(name="name", data_type="varchar(100)", nullable=True)
                },
                indexes=[IndexDefinition(name="idx_users_email", columns=["email"], unique=True)],
                row_count=100
            ),
            "products": TableDefinition(
                name="products",
                columns={
                    "id": ColumnDefinition(name="id", data_type="uuid", nullable=False, is_primary_key=True),
                    "name": ColumnDefinition(name="name", data_type="varchar(255)", nullable=False),
                    "price": ColumnDefinition(name="price", data_type="decimal(10,2)", nullable=False)
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
            "uploads": BucketDefinition(name="uploads", policy="private", object_count=25)
        }
    )


def test_compare_identical_schemas():
    print("\n[TEST] Comparing identical schemas...")
    service = SchemaDiffService()
    local_schema = create_sample_local_schema()
    cloud_schema = copy.deepcopy(local_schema)
    diff = service.compare_schemas(local_schema, cloud_schema)
    assert diff.total_changes == 0
    print("✅ PASSED")


def test_detect_added_columns():
    print("\n[TEST] Detecting added columns...")
    service = SchemaDiffService()
    local_schema = create_sample_local_schema()
    cloud_schema = copy.deepcopy(local_schema)
    cloud_schema.tables["users"].columns["phone"] = ColumnDefinition(name="phone", data_type="varchar(20)", nullable=True)
    diff = service.compare_schemas(local_schema, cloud_schema)
    added = [c for c in diff.added_changes if c.change_type == ChangeType.COLUMN_ADDED]
    assert len(added) == 1
    assert added[0].field_name == "phone"
    print("✅ PASSED")


def test_detect_removed_columns():
    print("\n[TEST] Detecting removed columns...")
    service = SchemaDiffService()
    local_schema = create_sample_local_schema()
    cloud_schema = copy.deepcopy(local_schema)
    del cloud_schema.tables["users"].columns["name"]
    diff = service.compare_schemas(local_schema, cloud_schema)
    removed = [c for c in diff.removed_changes if c.change_type == ChangeType.COLUMN_REMOVED]
    assert len(removed) == 1
    assert removed[0].severity == ChangeSeverity.CRITICAL
    print("✅ PASSED")


def test_breaking_changes():
    print("\n[TEST] Detecting breaking changes...")
    service = SchemaDiffService()
    local_schema = create_sample_local_schema()
    cloud_schema = copy.deepcopy(local_schema)
    del cloud_schema.tables["products"]
    diff = service.compare_schemas(local_schema, cloud_schema)
    assert diff.has_breaking_changes
    assert len(diff.breaking_changes) > 0
    print("✅ PASSED")


def test_migration_plan():
    print("\n[TEST] Generating migration plan...")
    service = SchemaDiffService()
    local_schema = create_sample_local_schema()
    cloud_schema = copy.deepcopy(local_schema)
    cloud_schema.tables["users"].columns["phone"] = ColumnDefinition(name="phone", data_type="varchar(20)", nullable=True)
    diff = service.compare_schemas(local_schema, cloud_schema)
    plan = service.generate_migration_plan(diff, uuid4())
    assert plan.total_steps > 0
    assert plan.is_safe
    print(f"✅ PASSED ({plan.total_steps} steps, {plan.estimated_total_duration_seconds}s)")


if __name__ == "__main__":
    print("=" * 60)
    print("Schema Diff Service Tests - Story #431")
    print("=" * 60)

    tests = [
        test_compare_identical_schemas,
        test_detect_added_columns,
        test_detect_removed_columns,
        test_breaking_changes,
        test_migration_plan
    ]

    passed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"❌ FAILED: {str(e)}")

    print("\n" + "=" * 60)
    print(f"Results: {passed}/{len(tests)} tests passed")
    print("=" * 60)
    exit(0 if passed == len(tests) else 1)
