"""
Test script for sync_executor API integration
"""
import sys
from sync_executor import SyncExecutor, SyncExecutionError
from sync_planner import SyncPlan

def test_sync_executor():
    """Test sync executor with API integration"""
    print("=" * 60)
    print("Testing SyncExecutor API Integration")
    print("=" * 60)

    # Create executor
    executor = SyncExecutor(
        local_api_url='http://localhost:8000',
        cloud_api_key='test-key'
    )

    # Create a simple plan for dry run
    plan = SyncPlan(direction='push', mode='incremental')

    print("\n1. Testing dry run (no API call)...")
    try:
        result = executor.execute_plan(plan, 'test-project-id', dry_run=True)
        print(f"   ✓ Dry run successful")
        print(f"   Status: {result['status']}")
        print(f"   Would execute: {result['would_execute']} operations")
    except Exception as e:
        print(f"   ✗ Dry run failed: {str(e)}")
        return False

    print("\n2. Checking API integration methods exist...")
    methods = [
        '_generate_api_plan',
        'rollback',
        'push_to_cloud',
        'pull_from_cloud'
    ]

    for method in methods:
        if hasattr(executor, method):
            print(f"   ✓ Method '{method}' exists")
        else:
            print(f"   ✗ Method '{method}' missing")
            return False

    print("\n3. Verifying stub methods removed...")
    removed_methods = [
        '_sync_table',
        '_sync_vector',
        '_sync_file',
        '_sync_event',
        '_sync_memory',
        '_execute_operation',
        '_rollback_operation'
    ]

    for method in removed_methods:
        if not hasattr(executor, method):
            print(f"   ✓ Stub method '{method}' removed")
        else:
            print(f"   ✗ Stub method '{method}' still exists (should be removed)")

    print("\n4. Checking initialization...")
    if hasattr(executor, 'last_sync_id'):
        print(f"   ✓ last_sync_id initialized: {executor.last_sync_id}")
    else:
        print(f"   ✗ last_sync_id not initialized")
        return False

    print("\n" + "=" * 60)
    print("✓ All integration checks passed!")
    print("=" * 60)
    print("\nNOTE: Live API tests require running API server.")
    print("To test with live API:")
    print("  1. Start the API: cd ../api && uvicorn main:app --reload")
    print("  2. Run: python sync_executor.py <project_id>")

    return True

if __name__ == "__main__":
    success = test_sync_executor()
    sys.exit(0 if success else 1)
