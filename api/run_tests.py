import sys
import os
import importlib.util

# Change to api directory
os.chdir('/Users/aideveloper/core/zerodb-local/api')

# Load schema_diff_service directly
spec = importlib.util.spec_from_file_location('schema_diff_service', 'services/schema_diff_service.py')
sds = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sds)

# Load schemas
spec2 = importlib.util.spec_from_file_location('schema_diff', 'schemas/schema_diff.py')
sd = importlib.util.module_from_spec(spec2)
spec2.loader.exec_module(sd)

from uuid import uuid4
import copy

def test_basic():
    print("[TEST] Basic schema comparison...")
    service = sds.SchemaDiffService()
    local = sd.SchemaDefinition(
        project_id=str(uuid4()),
        tables={"users": sd.TableDefinition(
            name="users",
            columns={"id": sd.ColumnDefinition(name="id", data_type="uuid", nullable=False)}
        )}
    )
    cloud = copy.deepcopy(local)
    diff = service.compare_schemas(local, cloud)
    assert diff.total_changes == 0
    print("✅ PASSED")

test_basic()
print("\n✅ All tests passed!")
