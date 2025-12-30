#!/usr/bin/env python3
"""
Standalone test for conflict resolver service.
Tests core functionality without requiring full database setup.
"""
import sys
from datetime import datetime, timedelta
from uuid import uuid4

# Add current directory to path
sys.path.insert(0, '/Users/aideveloper/core/zerodb-local/api')

from services.conflict_resolver import ConflictResolver, ConflictResolutionStrategy


def test_detect_conflicts():
    """Test conflict detection logic."""
    print("\n=== Test: Detect Conflicts ===")

    resolver = ConflictResolver()

    # Create test entities with same ID but different hashes
    local_entities = [{
        "entity_id": "vec_123",
        "entity_type": "vector",
        "data": {"embedding": [0.1, 0.2], "metadata": {"user": "alice"}},
        "updated_at": datetime.utcnow(),
        "hash": "local_hash_abc"
    }]

    cloud_entities = [{
        "entity_id": "vec_123",
        "entity_type": "vector",
        "data": {"embedding": [0.1, 0.2], "metadata": {"user": "bob"}},
        "updated_at": datetime.utcnow() - timedelta(hours=1),
        "hash": "cloud_hash_def"
    }]

    conflicts = resolver.detect_conflicts(local_entities, cloud_entities)

    print(f"✅ Detected {len(conflicts)} conflict(s)")
    assert len(conflicts) == 1, "Should detect 1 conflict"
    assert conflicts[0]["entity_id"] == "vec_123"
    print("✅ Conflict has correct entity_id")


def test_no_conflicts_identical_data():
    """Test no conflict when data is identical."""
    print("\n=== Test: No Conflicts (Identical Data) ===")

    resolver = ConflictResolver()

    entity = {
        "entity_id": "vec_456",
        "entity_type": "vector",
        "data": {"embedding": [0.3, 0.4]},
        "updated_at": datetime.utcnow(),
        "hash": "same_hash"
    }

    conflicts = resolver.detect_conflicts([entity], [entity])

    print(f"✅ Detected {len(conflicts)} conflict(s)")
    assert len(conflicts) == 0, "Should detect no conflicts"


def test_resolve_local_wins():
    """Test local-wins resolution strategy."""
    print("\n=== Test: Resolve Conflict (Local Wins) ===")

    resolver = ConflictResolver()

    conflict = {
        "entity_id": "vec_789",
        "entity_type": "vector",
        "local_version": {"data": "local", "updated_at": datetime.utcnow()},
        "cloud_version": {"data": "cloud", "updated_at": datetime.utcnow() - timedelta(hours=1)},
        "detected_at": datetime.utcnow()
    }

    resolution = resolver.resolve_conflict(conflict, ConflictResolutionStrategy.LOCAL_WINS)

    print(f"✅ Resolution strategy: {resolution['resolution']}")
    assert resolution["resolution"] == "local_wins"
    assert resolution["chosen_version"]["data"] == "local"
    print("✅ Local version chosen correctly")


def test_resolve_cloud_wins():
    """Test cloud-wins resolution strategy."""
    print("\n=== Test: Resolve Conflict (Cloud Wins) ===")

    resolver = ConflictResolver()

    conflict = {
        "entity_id": "vec_abc",
        "entity_type": "vector",
        "local_version": {"data": "local", "updated_at": datetime.utcnow()},
        "cloud_version": {"data": "cloud", "updated_at": datetime.utcnow() - timedelta(hours=1)},
        "detected_at": datetime.utcnow()
    }

    resolution = resolver.resolve_conflict(conflict, ConflictResolutionStrategy.CLOUD_WINS)

    print(f"✅ Resolution strategy: {resolution['resolution']}")
    assert resolution["resolution"] == "cloud_wins"
    assert resolution["chosen_version"]["data"] == "cloud"
    print("✅ Cloud version chosen correctly")


def test_resolve_newest_wins():
    """Test newest-wins resolution strategy."""
    print("\n=== Test: Resolve Conflict (Newest Wins) ===")

    resolver = ConflictResolver()

    local_timestamp = datetime.utcnow()
    cloud_timestamp = datetime.utcnow() - timedelta(hours=1)

    conflict = {
        "entity_id": "vec_def",
        "entity_type": "vector",
        "local_version": {"data": "local", "updated_at": local_timestamp},
        "cloud_version": {"data": "cloud", "updated_at": cloud_timestamp},
        "detected_at": datetime.utcnow()
    }

    resolution = resolver.resolve_conflict(conflict, ConflictResolutionStrategy.NEWEST_WINS)

    print(f"✅ Resolution strategy: {resolution['resolution']}")
    assert resolution["resolution"] == "newest_wins"
    assert resolution["chosen_version"]["data"] == "local", "Local is newer, should be chosen"
    print("✅ Newest version (local) chosen correctly")


def test_resolve_newest_wins_cloud_newer():
    """Test newest-wins when cloud is newer."""
    print("\n=== Test: Resolve Conflict (Newest Wins - Cloud Newer) ===")

    resolver = ConflictResolver()

    local_timestamp = datetime.utcnow() - timedelta(hours=2)
    cloud_timestamp = datetime.utcnow()

    conflict = {
        "entity_id": "vec_ghi",
        "entity_type": "vector",
        "local_version": {"data": "local", "updated_at": local_timestamp},
        "cloud_version": {"data": "cloud", "updated_at": cloud_timestamp},
        "detected_at": datetime.utcnow()
    }

    resolution = resolver.resolve_conflict(conflict, ConflictResolutionStrategy.NEWEST_WINS)

    print(f"✅ Resolution strategy: {resolution['resolution']}")
    assert resolution["resolution"] == "newest_wins"
    assert resolution["chosen_version"]["data"] == "cloud", "Cloud is newer, should be chosen"
    print("✅ Newest version (cloud) chosen correctly")


def test_invalid_strategy():
    """Test error handling for invalid strategy."""
    print("\n=== Test: Invalid Strategy Error ===")

    resolver = ConflictResolver()

    conflict = {
        "entity_id": "vec_jkl",
        "entity_type": "vector",
        "local_version": {"data": "local"},
        "cloud_version": {"data": "cloud"},
        "detected_at": datetime.utcnow()
    }

    try:
        resolver.resolve_conflict(conflict, "invalid_strategy")
        assert False, "Should raise ValueError"
    except ValueError as e:
        print(f"✅ Correctly raised ValueError: {str(e)}")


def test_resolve_all():
    """Test resolving multiple conflicts at once."""
    print("\n=== Test: Resolve All Conflicts ===")

    resolver = ConflictResolver()

    conflicts = [
        {
            "entity_id": f"vec_{i}",
            "entity_type": "vector",
            "local_version": {"data": f"local_{i}", "updated_at": datetime.utcnow()},
            "cloud_version": {"data": f"cloud_{i}", "updated_at": datetime.utcnow() - timedelta(hours=1)},
            "detected_at": datetime.utcnow()
        }
        for i in range(3)
    ]

    results = resolver.resolve_all(
        project_id=uuid4(),
        conflicts=conflicts,
        strategy=ConflictResolutionStrategy.LOCAL_WINS
    )

    print(f"✅ Resolved {len(results)} conflict(s)")
    assert len(results) == 3
    assert all(r["success"] for r in results)
    print("✅ All conflicts resolved successfully")


def main():
    """Run all tests."""
    print("="*60)
    print("Conflict Resolver Service - Standalone Tests")
    print("="*60)

    tests = [
        test_detect_conflicts,
        test_no_conflicts_identical_data,
        test_resolve_local_wins,
        test_resolve_cloud_wins,
        test_resolve_newest_wins,
        test_resolve_newest_wins_cloud_newer,
        test_invalid_strategy,
        test_resolve_all
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            failed += 1
            print(f"❌ Test failed: {test.__name__}")
            print(f"   Error: {str(e)}")
            import traceback
            traceback.print_exc()

    print("\n" + "="*60)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("="*60)

    if failed > 0:
        sys.exit(1)
    else:
        print("\n✅ All tests passed!")
        sys.exit(0)


if __name__ == "__main__":
    main()
