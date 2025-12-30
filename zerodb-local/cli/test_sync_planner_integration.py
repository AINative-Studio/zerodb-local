#!/usr/bin/env python3
"""
Test script to verify sync_planner.py API integration
"""
import sys
from sync_planner import SyncPlanner, SyncPlannerError

def test_sync_planner_integration():
    """Test that sync_planner calls real API"""
    print("Testing sync_planner.py API integration...\n")

    # Create planner instance
    planner = SyncPlanner(
        local_api_url='http://localhost:8000',
        api_key=None  # No auth for local testing
    )

    print("✓ SyncPlanner initialized with API URL: http://localhost:8000")

    # Test project ID (UUID format required)
    test_project_id = '12345678-1234-1234-1234-123456789012'

    try:
        # Try to generate a plan
        print(f"✓ Attempting to generate sync plan for project: {test_project_id}")
        plan = planner.generate_plan(
            project_id=test_project_id,
            direction='push',
            mode='full',
            filters={'entities': ['vectors', 'tables']}
        )

        print(f"\n✓ SUCCESS: Received plan with {len(plan.operations)} operations")
        print(f"  - Direction: {plan.direction}")
        print(f"  - Mode: {plan.mode}")
        print(f"  - Total operations: {plan.total_operations}")

        if plan.operations:
            print("\n  First operation:")
            op = plan.operations[0]
            print(f"    - Type: {op.entity_type}")
            print(f"    - Operation: {op.operation}")
            print(f"    - Description: {op.description}")
            print("\n✅ INTEGRATION WORKING - API is being called!")
        else:
            print("\n⚠️  Plan has no operations (API returned empty plan)")

        return True

    except SyncPlannerError as e:
        # This is expected if API is not running
        if "API request failed" in str(e):
            print(f"\n❌ API NOT RUNNING: {e}")
            print("\n   To test integration:")
            print("   1. Start the API: cd /Users/aideveloper/core/zerodb-local/api && uvicorn main:app --reload")
            print("   2. Run this test again")
            return False
        else:
            print(f"\n❌ ERROR: {e}")
            return False

    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_sync_planner_integration()
    sys.exit(0 if success else 1)
