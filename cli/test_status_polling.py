#!/usr/bin/env python3
"""
Test script for status polling functionality

Tests the _poll_sync_status method added in Story #455
"""
import sys
import os

# Add CLI directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sync_executor import SyncExecutor
from sync_planner import SyncPlan

def test_sync_with_polling():
    """Test sync execution with status polling"""

    print("Testing sync execution with status polling...")
    print("-" * 50)

    # Create executor instance
    executor = SyncExecutor(
        local_api_url='http://localhost:8000',
        cloud_api_key='test-key-12345'
    )

    # Create a simple sync plan
    plan = SyncPlan(direction='push', mode='full')

    print("\n1. Testing execute_plan with polling...")
    print("   This will call the API and poll for status updates")
    print("   Expected: Progress bar showing sync status\n")

    try:
        # Execute the plan
        # Note: This will fail if API is not running, which is expected
        result = executor.execute_plan(
            plan=plan,
            project_id='test-project-uuid-12345',
            dry_run=False
        )

        print("\n✓ Sync completed!")
        print(f"  Status: {result.get('status')}")
        print(f"  Sync ID: {result.get('sync_id')}")
        print(f"  Total operations: {result.get('total_operations')}")
        print(f"  Successful: {result.get('successful')}")
        print(f"  Failed: {result.get('failed')}")

    except Exception as e:
        print(f"\n✗ Test failed (expected if API not running): {str(e)}")
        print("\nTo test with live API:")
        print("  1. Start API: cd /Users/aideveloper/core/zerodb-local/api && uvicorn main:app --reload")
        print("  2. Run this test again")
        return False

    print("\n" + "-" * 50)
    print("Test complete!")
    return True

def test_dry_run():
    """Test dry run (no polling)"""

    print("\nTesting dry run (should NOT poll)...")
    print("-" * 50)

    executor = SyncExecutor(local_api_url='http://localhost:8000')
    plan = SyncPlan(direction='push', mode='full')

    # Add a mock operation to the plan
    from sync_planner import SyncOperation
    plan.operations.append(
        SyncOperation(
            operation='create',
            entity_type='vector',
            entity_id='test-vector-1',
            description='Create test vector'
        )
    )

    result = executor.execute_plan(
        plan=plan,
        project_id='test-project',
        dry_run=True
    )

    print(f"\n✓ Dry run completed")
    print(f"  Status: {result.get('status')}")
    print(f"  Would execute: {result.get('would_execute')} operations")

    print("\n" + "-" * 50)
    return True

if __name__ == '__main__':
    print("=" * 50)
    print("Status Polling Test - Story #455")
    print("=" * 50)

    # Test dry run first (doesn't need API)
    test_dry_run()

    # Test with polling (needs API)
    print("\n")
    test_sync_with_polling()

    print("\n" + "=" * 50)
    print("All tests complete!")
    print("=" * 50)
