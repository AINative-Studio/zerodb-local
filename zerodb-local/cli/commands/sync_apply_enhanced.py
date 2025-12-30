"""
Enhanced Sync Apply Command for Story #422

Implements all requirements for Story #422: Sync Apply Command with:
- --auto-approve flag
- --direction option
- --rollback-on-error option
- --plan-id option
- Enhanced confirmation prompts
- Progress tracking
- Sync history
- Comprehensive error handling
"""
import typer
import time
from typing import Optional
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from datetime import datetime
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from ..sync_planner import SyncPlanner
    from ..sync_executor import SyncExecutor, SyncExecutionError
    from ..conflict_resolver import ConflictResolver
    from ..config import load_config, get_cloud_credentials
    from .sync_enhanced import (
        show_confirmation_prompt,
        save_sync_history,
        load_plan_by_id,
        display_results_enhanced
    )
except ImportError:
    from sync_planner import SyncPlanner
    from sync_executor import SyncExecutor, SyncExecutionError
    from conflict_resolver import ConflictResolver
    from config import load_config, get_cloud_credentials
    from sync_enhanced import (
        show_confirmation_prompt,
        save_sync_history,
        load_plan_by_id,
        display_results_enhanced
    )

console = Console()


def sync_apply_command(
    auto_approve: bool = False,
    direction: str = "push",
    rollback_on_error: bool = True,
    plan_id: Optional[str] = None,
    conflict_strategy: str = "manual",
    dry_run: bool = False
):
    """
    Execute sync plan and apply changes

    Story #422: Sync Apply Command

    Args:
        auto_approve: Skip confirmation prompt
        direction: Sync direction (push/pull/bidirectional)
        rollback_on_error: Auto-rollback on failure
        plan_id: Execute specific plan by ID
        conflict_strategy: Conflict resolution strategy
        dry_run: Preview without executing

    Examples:
        zerodb sync apply
        zerodb sync apply --auto-approve
        zerodb sync apply --direction push
        zerodb sync apply --direction pull
        zerodb sync apply --rollback-on-error
        zerodb sync apply --plan-id abc123
    """
    try:
        # Load configuration
        config = load_config()
        project_id = config.get('project_id')

        if not project_id:
            console.print("[red]Error:[/red] No project linked. Run 'zerodb cloud link <project_id>' first.")
            raise typer.Exit(1)

        # Get cloud credentials
        credentials = get_cloud_credentials()
        if not credentials:
            console.print("[red]Error:[/red] Not logged in. Run 'zerodb cloud login' first.")
            raise typer.Exit(1)

        # Validate direction
        valid_directions = ['push', 'pull', 'bidirectional']
        if direction not in valid_directions:
            console.print(f"[red]Error:[/red] Invalid direction '{direction}'. Must be one of: {', '.join(valid_directions)}")
            raise typer.Exit(1)

        # Create components
        planner = SyncPlanner()
        executor = SyncExecutor(cloud_api_key=credentials.get('access_token'))
        resolver = ConflictResolver(default_strategy=conflict_strategy)

        # Load or generate plan
        if plan_id:
            console.print(f"[cyan]Loading sync plan {plan_id}...[/cyan]")
            plan = load_plan_by_id(plan_id)
            if not plan:
                # Plan ID not found, generate new plan
                console.print("[yellow]Plan not found. Generating new plan...[/yellow]")
                plan = planner.generate_plan(project_id=project_id, direction=direction, mode='incremental')
        else:
            console.print(f"[cyan]Generating sync plan ({direction})...[/cyan]")
            plan = planner.generate_plan(project_id=project_id, direction=direction, mode='incremental')

        # Check if there are any operations
        if plan.total_operations == 0:
            console.print("[green]✓[/green] No changes to sync. Everything is up to date.")
            return

        # Display plan
        from .sync_enhanced import display_plan_enhanced
        display_plan_enhanced(plan, direction)

        # Check for conflicts
        if plan.has_conflicts:
            console.print(f"\n[yellow]⚠️  {len(plan.conflicts)} conflict(s) detected[/yellow]")
            resolved = resolver.resolve_all(plan.conflicts, strategy=conflict_strategy)

            # Update plan with resolved values
            # TODO: Apply resolved values to plan operations

            resolver.display_summary()

        # Enhanced confirmation prompt (unless --auto-approve or --dry-run)
        if not auto_approve and not dry_run:
            show_confirmation_prompt(plan, direction)
            if not typer.confirm("\nProceed?"):
                console.print("[yellow]Sync cancelled[/yellow]")
                return

        # Execute plan with progress tracking
        start_time = time.time()

        if dry_run:
            console.print(f"\n[cyan]🔍 Dry run mode - no changes will be made[/cyan]")
            result = executor.execute_plan(plan, project_id, dry_run=True)
            execution_time = time.time() - start_time
            display_results_enhanced(result, dry_run, execution_time)
            return

        # Real execution
        console.print(f"\n[cyan]Executing sync plan...[/cyan]")

        try:
            # Execute with progress bar
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                console=console
            ) as progress:
                task = progress.add_task(
                    f"Syncing ({direction})...",
                    total=plan.total_operations
                )

                # Execute plan
                result = executor.execute_plan(
                    plan,
                    project_id,
                    dry_run=False,
                    progress_callback=lambda desc, current, total: progress.update(
                        task,
                        completed=current,
                        description=desc
                    )
                )

            execution_time = time.time() - start_time

            # Display results
            display_results_enhanced(result, False, execution_time)

            # Save to sync history
            save_sync_history(plan, result, execution_time, direction)

            # Show sync_id for rollback reference
            if result.get('status') == 'success':
                sync_id = result.get('sync_id', f"sync_{int(time.time())}")
                console.print(f"\n[dim]Sync ID: {sync_id} (for rollback reference)[/dim]")
                console.print("\n[bold green]✅ Sync completed successfully[/bold green]")

        except SyncExecutionError as e:
            execution_time = time.time() - start_time

            if rollback_on_error:
                console.print("\n[yellow]⚠️  Error detected. Rolling back changes...[/yellow]")
                try:
                    executor.rollback()
                    console.print("[green]✓[/green] Rollback complete. Database restored.")
                except Exception as rollback_error:
                    console.print(f"[red]✗[/red] Rollback failed: {str(rollback_error)}")

            # Save failed sync to history
            result = {
                'status': 'failed',
                'total_operations': plan.total_operations,
                'successful': 0,
                'failed': plan.total_operations,
                'errors': [{'operation': 'sync', 'error': str(e)}]
            }
            save_sync_history(plan, result, execution_time, direction)

            console.print(f"\n[red]❌ Sync failed:[/red] {str(e)}")
            raise typer.Exit(1)

        except KeyboardInterrupt:
            execution_time = time.time() - start_time
            console.print("\n[yellow]⚠️  Sync interrupted by user[/yellow]")

            if rollback_on_error:
                console.print("[yellow]Rolling back changes...[/yellow]")
                try:
                    executor.rollback()
                    console.print("[green]✓[/green] Rollback complete")
                except Exception as rollback_error:
                    console.print(f"[red]✗[/red] Rollback failed: {str(rollback_error)}")

            # Save interrupted sync to history
            result = {
                'status': 'cancelled',
                'total_operations': plan.total_operations,
                'successful': 0,
                'failed': plan.total_operations,
                'errors': [{'operation': 'sync', 'error': 'User interrupted'}]
            }
            save_sync_history(plan, result, execution_time, direction)

            raise typer.Exit(130)

    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {str(e)}")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        raise typer.Exit(1)


# Specific error handling for common scenarios
def handle_network_error(error: Exception):
    """Handle network interruption errors"""
    console.print("\n[red]❌ Connection lost[/red]")
    console.print(f"Details: {str(error)}")
    console.print("\n[yellow]Suggestions:[/yellow]")
    console.print("  1. Check your internet connection")
    console.print("  2. Verify cloud API URL in config")
    console.print("  3. Check if cloud service is online")


def handle_schema_conflict_error(error: Exception):
    """Handle breaking schema change errors"""
    console.print("\n[red]❌ Breaking schema change detected[/red]")
    console.print(f"Details: {str(error)}")
    console.print("\n[yellow]Aborting sync to prevent data loss.[/yellow]")
    console.print("\n[yellow]Suggestions:[/yellow]")
    console.print("  1. Review schema changes with 'zerodb sync plan --schema'")
    console.print("  2. Create a backup before proceeding")
    console.print("  3. Use 'zerodb sync apply --force' to override (dangerous)")


def handle_disk_space_error(required_mb: int):
    """Handle insufficient disk space errors"""
    console.print("\n[red]❌ Insufficient disk space[/red]")
    console.print(f"Need {required_mb} MB free space")
    console.print("\n[yellow]Suggestions:[/yellow]")
    console.print("  1. Free up disk space")
    console.print("  2. Change local database directory")
    console.print("  3. Use selective sync to reduce data size")


def handle_quota_exceeded_error():
    """Handle cloud quota exceeded errors"""
    console.print("\n[red]❌ Cloud storage quota exceeded[/red]")
    console.print("\n[yellow]Suggestions:[/yellow]")
    console.print("  1. Upgrade your cloud plan")
    console.print("  2. Delete old data from cloud")
    console.print("  3. Use selective sync to reduce data")
    console.print("  4. Contact support for quota increase")
