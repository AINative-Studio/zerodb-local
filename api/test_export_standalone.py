"""
Standalone Export Service Tests
Tests export bundle creation without full test infrastructure
"""
import asyncio
import json
import zipfile
import io
from uuid import uuid4
from datetime import datetime

# Test imports - import directly to avoid __init__ loading all services
import sys
sys.path.insert(0, '/Users/aideveloper/core/zerodb-local/api')

from schemas.export import (
    VectorExport,
    TableExport,
    FileExport,
    EventExport,
    MemoryExport,
    ExportBundle,
    BundleManifest,
    RecordCounts
)

# Import ExportService class directly to avoid loading other services
from services.export_service import ExportService


async def test_package_bundle():
    """Test that package_bundle creates a valid ZIP file"""
    print("\n🧪 Testing package_bundle creation...")

    # Create test bundle
    manifest = BundleManifest(
        bundle_id=uuid4(),
        project_id=uuid4(),
        export_type="full",
        created_at=datetime.utcnow(),
        entity_counts=RecordCounts(vectors=2, tables=1, events=1, memory=1),
        files=[]
    )

    bundle = ExportBundle(
        manifest=manifest,
        vectors=[
            VectorExport(
                vector_id="vec1",
                namespace="default",
                document="Test document 1",
                metadata={"tag": "test"},
                embedding=[0.1, 0.2, 0.3],
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            ),
            VectorExport(
                vector_id="vec2",
                namespace="custom",
                document="Test document 2",
                metadata={"tag": "prod"},
                embedding=[0.4, 0.5, 0.6],
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
        ],
        tables=[
            TableExport(
                table_id="tbl1",
                table_name="users",
                schema={"fields": {"name": "string", "age": "integer"}},
                description="User table",
                rows=[
                    {"name": "Alice", "age": 30},
                    {"name": "Bob", "age": 25}
                ],
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
        ],
        events=[
            EventExport(
                event_id="evt1",
                event_type="user.created",
                event_data={"user_id": "123"},
                source="api",
                correlation_id="corr-1",
                created_at=datetime.utcnow()
            )
        ],
        memory=[
            MemoryExport(
                memory_id="mem1",
                agent_id="agent1",
                session_id="session1",
                role="user",
                content="Hello, how are you?",
                metadata={},
                embedding=[0.7, 0.8],
                created_at=datetime.utcnow()
            )
        ]
    )

    # Package bundle
    service = ExportService()
    bundle_bytes = await service.package_bundle(bundle)

    # Verify it's a valid ZIP
    assert isinstance(bundle_bytes, bytes), "Bundle should be bytes"
    assert len(bundle_bytes) > 0, "Bundle should not be empty"
    print(f"✓ Bundle created: {len(bundle_bytes)} bytes")

    # Open and verify contents
    zip_file = zipfile.ZipFile(io.BytesIO(bundle_bytes), 'r')
    file_list = zip_file.namelist()
    print(f"✓ ZIP contains {len(file_list)} files: {file_list}")

    # Verify expected files
    assert 'manifest.json' in file_list, "Should contain manifest.json"
    assert 'vectors.jsonl' in file_list, "Should contain vectors.jsonl"
    assert 'tables/users.jsonl' in file_list, "Should contain tables/users.jsonl"
    assert 'events.jsonl' in file_list, "Should contain events.jsonl"
    assert 'memory.jsonl' in file_list, "Should contain memory.jsonl"
    print("✓ All expected files present")

    # Verify manifest contents
    manifest_data = json.loads(zip_file.read('manifest.json'))
    assert manifest_data['entity_counts']['vectors'] == 2
    assert manifest_data['entity_counts']['tables'] == 1
    assert manifest_data['entity_counts']['events'] == 1
    assert manifest_data['entity_counts']['memory'] == 1
    print("✓ Manifest counts correct")

    # Verify vectors.jsonl format (JSONL = one JSON per line)
    vectors_content = zip_file.read('vectors.jsonl').decode('utf-8')
    vector_lines = vectors_content.strip().split('\n')
    assert len(vector_lines) == 2, "Should have 2 vector lines"

    vector1 = json.loads(vector_lines[0])
    assert vector1['vector_id'] in ['vec1', 'vec2']
    assert 'embedding' in vector1
    assert 'metadata' in vector1
    print("✓ Vectors JSONL format correct")

    # Verify table JSONL format (metadata + rows)
    table_content = zip_file.read('tables/users.jsonl').decode('utf-8')
    table_lines = table_content.strip().split('\n')
    assert len(table_lines) == 3, "Should have 1 metadata line + 2 row lines"

    table_meta = json.loads(table_lines[0])
    assert table_meta['table_name'] == 'users'
    assert table_meta['row_count'] == 2

    row1 = json.loads(table_lines[1])
    assert 'name' in row1
    print("✓ Table JSONL format correct")

    # Verify events.jsonl
    events_content = zip_file.read('events.jsonl').decode('utf-8')
    event_lines = events_content.strip().split('\n')
    assert len(event_lines) == 1
    event1 = json.loads(event_lines[0])
    assert event1['event_type'] == 'user.created'
    print("✓ Events JSONL format correct")

    # Verify memory.jsonl
    memory_content = zip_file.read('memory.jsonl').decode('utf-8')
    memory_lines = memory_content.strip().split('\n')
    assert len(memory_lines) == 1
    mem1 = json.loads(memory_lines[0])
    assert mem1['role'] == 'user'
    assert mem1['content'] == 'Hello, how are you?'
    print("✓ Memory JSONL format correct")

    print("\n✅ All package_bundle tests passed!")
    return True


async def test_schema_models():
    """Test that all export schemas are properly structured"""
    print("\n🧪 Testing export schemas...")

    # Test VectorExport
    vector = VectorExport(
        vector_id="test_vec",
        namespace="default",
        document="Test document",
        metadata={"key": "value"},
        embedding=[0.1, 0.2, 0.3],
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    assert vector.vector_id == "test_vec"
    print("✓ VectorExport schema valid")

    # Test TableExport
    table = TableExport(
        table_id="test_table",
        table_name="users",
        schema={"fields": {}},
        rows=[{"name": "Alice"}],
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    assert table.table_name == "users"
    assert len(table.rows) == 1
    print("✓ TableExport schema valid")

    # Test FileExport
    file = FileExport(
        file_id="test_file",
        file_name="document.pdf",
        content_type="application/pdf",
        folder="docs",
        metadata={},
        size_bytes=1024,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    assert file.file_name == "document.pdf"
    print("✓ FileExport schema valid")

    # Test EventExport
    event = EventExport(
        event_id="test_event",
        event_type="test.event",
        event_data={"action": "test"},
        source="test",
        created_at=datetime.utcnow()
    )
    assert event.event_type == "test.event"
    print("✓ EventExport schema valid")

    # Test MemoryExport
    memory = MemoryExport(
        memory_id="test_mem",
        agent_id="agent1",
        session_id="session1",
        role="user",
        content="Test message",
        metadata={},
        created_at=datetime.utcnow()
    )
    assert memory.role == "user"
    print("✓ MemoryExport schema valid")

    # Test RecordCounts
    counts = RecordCounts(
        vectors=10,
        tables=5,
        table_rows=100,
        memory=20,
        events=30,
        files=15
    )
    assert counts.vectors == 10
    assert counts.table_rows == 100
    print("✓ RecordCounts schema valid")

    # Test BundleManifest
    manifest = BundleManifest(
        bundle_id=uuid4(),
        project_id=uuid4(),
        export_type="full",
        created_at=datetime.utcnow(),
        entity_counts=counts,
        files=["manifest.json", "vectors.jsonl"]
    )
    assert manifest.export_type == "full"
    assert len(manifest.files) == 2
    print("✓ BundleManifest schema valid")

    print("\n✅ All schema tests passed!")
    return True


async def main():
    """Run all standalone tests"""
    print("=" * 60)
    print("ZeroDB Export Service - Standalone Tests")
    print("=" * 60)

    try:
        # Run tests
        await test_schema_models()
        await test_package_bundle()

        print("\n" + "=" * 60)
        print("🎉 ALL TESTS PASSED!")
        print("=" * 60)
        return 0
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
