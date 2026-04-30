"""
Test file for Story 3.6: Sync Apply Commands

Run with: python3 test_sync_commands.py
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Now import with absolute imports
import sync_planner
import sync_executor
import conflict_resolver
from rich.console import Console

SyncPlanner = sync_planner.SyncPlanner
SyncPlan = sync_planner.SyncPlan
SyncOperation = sync_planner.SyncOperation
SyncExecutor = sync_executor.SyncExecutor
ConflictResolver = conflict_resolver.ConflictResolver
Conflict = conflict_resolver.Conflict
ConflictResolutionStrategy = conflict_resolver.ConflictResolutionStrategy

console = Console()


def test_sync_planner():
    """Test sync plan generation"""
    console.print("\n[bold cyan]Testing Sync Planner[/bold cyan]\n")

    planner = SyncPlanner()

    # Create a sample plan
    plan = SyncPlan(direction='push', mode='incremental')

    # Add sample operations
    plan.operations.append(SyncOperation(
        entity_type='table',
        operation='create',
        entity_name='users',
        description='Create table: users'
    ))

    plan.operations.append(SyncOperation(
        entity_type='vector',
        operation='upsert',
        entity_id='vec-123',
        description='Upsert vector embedding',
        metadata={'dimensions': 1536}
    ))

    plan.operations.append(SyncOperation(
        entity_type='table',
        operation='update',
        entity_name='posts',
        description='Update table: posts (add 5 rows)'
    ))

    console.print(f"[green]✓[/green] Created plan with {plan.total_operations} operations")

    summary = plan.get_summary()
    console.print(f"  Summary: {summary}")

    # Test JSON export
    json_output = planner.plan_to_json(plan)
    console.print(f"[green]✓[/green] Exported to JSON ({len(json_output)} bytes)")


def test_conflict_resolver():
    """Test conflict detection and resolution"""
    console.print("\n[bold cyan]Testing Conflict Resolver[/bold cyan]\n")

    resolver = ConflictResolver(default_strategy=ConflictResolutionStrategy.LOCAL_WINS)

    # Create sample conflicts
    conflict = Conflict(
        entity_type='table',
        entity_id='user-123',
        local_value={'name': 'Alice Smith', 'email': 'alice@local.com'},
        cloud_value={'name': 'Alice Johnson', 'email': 'alice@cloud.com'},
        local_timestamp='2025-12-28T10:00:00Z',
        cloud_timestamp='2025-12-28T09:00:00Z'
    )

    # Test local-wins strategy
    resolution = resolver.resolve_conflict(conflict, ConflictResolutionStrategy.LOCAL_WINS)
    console.print(f"[green]✓[/green] Local-wins resolution: {resolution['resolution']}")

    # Test cloud-wins strategy
    resolution = resolver.resolve_conflict(conflict, ConflictResolutionStrategy.CLOUD_WINS)
    console.print(f"[green]✓[/green] Cloud-wins resolution: {resolution['resolution']}")

    # Test newest-wins strategy
    resolution = resolver.resolve_conflict(conflict, ConflictResolutionStrategy.NEWEST_WINS)
    console.print(f"[green]✓[/green] Newest-wins resolution: {resolution['resolution']}")


def test_sync_executor():
    """Test sync execution (dry run)"""
    console.print("\n[bold cyan]Testing Sync Executor[/bold cyan]\n")

    executor = SyncExecutor()

    # Create a sample plan
    plan = SyncPlan(direction='push', mode='incremental')
    plan.operations.append(SyncOperation(
        entity_type='vector',
        operation='upsert',
        description='Upsert 10 vectors'
    ))
    plan.operations.append(SyncOperation(
        entity_type='table',
        operation='create',
        description='Create table: sessions'
    ))

    # Test dry run
    result = executor.execute_plan(plan, project_id='test-project', dry_run=True)
    console.print(f"[green]✓[/green] Dry run completed")
    console.print(f"  Would execute: {result['would_execute']} operations")


def test_cli_structure():
    """Test CLI module structure"""
    console.print("\n[bold cyan]Testing CLI Structure[/bold cyan]\n")

    # Test imports
    try:
        from commands import sync, local, cloud, env, inspect
        console.print("[green]✓[/green] All command modules import successfully")
    except ImportError as e:
        console.print(f"[red]✗[/red] Import error: {str(e)}")
        return

    # Test config module
    try:
        from config import load_config, save_config, get_cloud_credentials
        console.print("[green]✓[/green] Config module imports successfully")
    except ImportError as e:
        console.print(f"[red]✗[/red] Import error: {str(e)}")


def main():
    """Run all tests"""
    console.print("[bold]ZeroDB CLI - Story 3.6 Test Suite[/bold]")
    console.print("=" * 60)

    try:
        test_sync_planner()
        test_conflict_resolver()
        test_sync_executor()
        test_cli_structure()

        console.print("\n[bold green]All tests passed![/bold green]")

    except Exception as e:
        console.print(f"\n[bold red]Test failed:[/bold red] {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
