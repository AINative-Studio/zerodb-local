"""
Sync Commands - Manage sync between local and cloud

Implements Story 3.5 (sync plan) and Story 3.6 (sync apply)
"""
import typer
from typing import Optional, List
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
import json
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from ..sync_planner import SyncPlanner, SyncPlan
    from ..sync_executor import SyncExecutor, SyncExecutionError
    from ..conflict_resolver import ConflictResolver, ConflictResolutionStrategy
    from ..config import load_config, get_cloud_credentials
except ImportError:
    from sync_planner import SyncPlanner, SyncPlan
    from sync_executor import SyncExecutor, SyncExecutionError
    from conflict_resolver import ConflictResolver, ConflictResolutionStrategy
    from config import load_config, get_cloud_credentials

app = typer.Typer(help="Sync between local and cloud")
console = Console()


@app.command("plan")
def sync_plan(
    schema: bool = typer.Option(False, "--schema", help="Show schema diff only"),
    data: bool = typer.Option(False, "--data", help="Show data diff only"),
    vectors: bool = typer.Option(False, "--vectors", help="Show vector diff only"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
    direction: str = typer.Option("push", "--direction", "-d", help="Sync direction: push, pull, bidirectional")
):
    """
    Generate and display sync plan showing differences

    Story 3.5: Sync Plan Command

    Examples:
        zerodb sync plan
        zerodb sync plan --schema
        zerodb sync plan --vectors --json
    """
    try:
        config = load_config()
        project_id = config.get('project_id')

        if not project_id:
            console.print("[red]Error:[/red] No project linked. Run 'zerodb cloud link <project_id>' first.")
            raise typer.Exit(1)

        # Create planner
        planner = SyncPlanner()

        # Determine filters based on flags
        filters = None
        if schema or data or vectors:
            entities = []
            if schema:
                entities.append('tables')
            if data:
                entities.append('tables')
            if vectors:
                entities.append('vectors')
            filters = {'entities': entities}

        # Generate plan
        console.print(f"[cyan]Generating sync plan for project {project_id}...[/cyan]")
        plan = planner.generate_plan(
            project_id=project_id,
            direction=direction,
            mode='incremental',
            filters=filters
        )

        # Output
        if json_output:
            console.print(planner.plan_to_json(plan))
        else:
            _display_plan(plan)

    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        raise typer.Exit(1)


@app.command("apply")
def sync_apply(
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be done without executing"),
    conflict_strategy: str = typer.Option(
        "manual",
        "--strategy",
        "-s",
        help="Conflict resolution strategy: local-wins, cloud-wins, newest-wins, manual"
    )
):
    """
    Execute sync plan and apply changes

    Story 3.6: Sync Apply Command

    Examples:
        zerodb sync apply
        zerodb sync apply --yes
        zerodb sync apply --dry-run
        zerodb sync apply --strategy=local-wins
    """
    try:
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

        # Create components
        planner = SyncPlanner()
        executor = SyncExecutor(cloud_api_key=credentials.get('access_token'))
        resolver = ConflictResolver(default_strategy=conflict_strategy)

        # Generate plan
        console.print(f"[cyan]Generating sync plan...[/cyan]")
        plan = planner.generate_plan(project_id=project_id, direction='push', mode='incremental')

        if plan.total_operations == 0:
            console.print("[green]✓[/green] No changes to sync. Everything is up to date.")
            return

        # Display plan
        _display_plan(plan)

        # Check for conflicts
        if plan.has_conflicts:
            console.print(f"\n[yellow]⚠️  {len(plan.conflicts)} conflict(s) detected[/yellow]")
            resolved = resolver.resolve_all(plan.conflicts, strategy=conflict_strategy)

            # Update plan with resolved values
            # TODO: Apply resolved values to plan operations

            resolver.display_summary()

        # Confirmation prompt (unless --yes or --dry-run)
        if not yes and not dry_run:
            if not typer.confirm(f"\nApply {plan.total_operations} operation(s)?"):
                console.print("[yellow]Sync cancelled[/yellow]")
                return

        # Execute plan
        console.print(f"\n[cyan]Executing sync plan...[/cyan]")
        result = executor.execute_plan(plan, project_id, dry_run=dry_run)

        # Display results
        _display_results(result, dry_run)

    except SyncExecutionError as e:
        console.print(f"[red]Sync failed:[/red] {str(e)}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        raise typer.Exit(1)


@app.command("push")
def sync_push(
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
    force: bool = typer.Option(False, "--force", help="Force push, overwriting cloud data")
):
    """
    Push local changes to cloud

    Shorthand for: zerodb sync apply (with direction=push)

    Examples:
        zerodb sync push
        zerodb sync push --yes
        zerodb sync push --force
    """
    try:
        config = load_config()
        project_id = config.get('project_id')

        if not project_id:
            console.print("[red]Error:[/red] No project linked. Run 'zerodb cloud link <project_id>' first.")
            raise typer.Exit(1)

        credentials = get_cloud_credentials()
        if not credentials:
            console.print("[red]Error:[/red] Not logged in. Run 'zerodb cloud login' first.")
            raise typer.Exit(1)

        # Create components
        planner = SyncPlanner()
        executor = SyncExecutor(cloud_api_key=credentials.get('access_token'))

        # Determine strategy
        strategy = ConflictResolutionStrategy.LOCAL_WINS if force else ConflictResolutionStrategy.MANUAL
        resolver = ConflictResolver(default_strategy=strategy)

        # Generate and execute plan
        console.print(f"[cyan]Pushing to cloud...[/cyan]")
        plan = planner.generate_plan(project_id=project_id, direction='push', mode='incremental')

        if plan.total_operations == 0:
            console.print("[green]✓[/green] No changes to push. Everything is up to date.")
            return

        _display_plan(plan)

        # Handle conflicts
        if plan.has_conflicts and not force:
            console.print(f"\n[yellow]⚠️  {len(plan.conflicts)} conflict(s) detected[/yellow]")
            resolved = resolver.resolve_all(plan.conflicts, strategy=strategy)
            resolver.display_summary()

        # Confirmation
        if not yes:
            if not typer.confirm(f"\nPush {plan.total_operations} operation(s) to cloud?"):
                console.print("[yellow]Push cancelled[/yellow]")
                return

        # Execute
        result = executor.execute_plan(plan, project_id)
        _display_results(result)

        console.print(f"\n[green]✓[/green] Successfully pushed to cloud")

    except SyncExecutionError as e:
        console.print(f"[red]Push failed:[/red] {str(e)}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        raise typer.Exit(1)


@app.command("pull")
def sync_pull(
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
):
    """
    Pull cloud changes to local

    Shorthand for: zerodb sync apply (with direction=pull)

    Examples:
        zerodb sync pull
        zerodb sync pull --yes
    """
    try:
        config = load_config()
        project_id = config.get('project_id')

        if not project_id:
            console.print("[red]Error:[/red] No project linked. Run 'zerodb cloud link <project_id>' first.")
            raise typer.Exit(1)

        credentials = get_cloud_credentials()
        if not credentials:
            console.print("[red]Error:[/red] Not logged in. Run 'zerodb cloud login' first.")
            raise typer.Exit(1)

        # Create components
        planner = SyncPlanner()
        executor = SyncExecutor(cloud_api_key=credentials.get('access_token'))
        resolver = ConflictResolver(default_strategy=ConflictResolutionStrategy.MANUAL)

        # Generate and execute plan
        console.print(f"[cyan]Pulling from cloud...[/cyan]")
        plan = planner.generate_plan(project_id=project_id, direction='pull', mode='incremental')

        if plan.total_operations == 0:
            console.print("[green]✓[/green] No changes to pull. Everything is up to date.")
            return

        _display_plan(plan)

        # Handle conflicts
        if plan.has_conflicts:
            console.print(f"\n[yellow]⚠️  {len(plan.conflicts)} conflict(s) detected[/yellow]")
            resolved = resolver.resolve_all(plan.conflicts)
            resolver.display_summary()

        # Confirmation
        if not yes:
            if not typer.confirm(f"\nPull {plan.total_operations} operation(s) from cloud?"):
                console.print("[yellow]Pull cancelled[/yellow]")
                return

        # Execute
        result = executor.execute_plan(plan, project_id)
        _display_results(result)

        console.print(f"\n[green]✓[/green] Successfully pulled from cloud")

    except SyncExecutionError as e:
        console.print(f"[red]Pull failed:[/red] {str(e)}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        raise typer.Exit(1)


def _display_plan(plan: SyncPlan):
    """Display sync plan in a nice format"""
    console.print(f"\n[bold cyan]🔍 Sync Plan ({plan.direction})[/bold cyan]\n")

    summary = plan.get_summary()

    # Summary table
    table = Table(title="Summary")
    table.add_column("Operation", style="cyan")
    table.add_column("Count", style="magenta", justify="right")

    for op_type, count in summary.items():
        if op_type != 'total' and count > 0:
            icon = "+" if op_type == "create" else "~" if op_type == "update" else "-" if op_type == "delete" else "↑"
            table.add_row(f"{icon} {op_type.title()}", str(count))

    console.print(table)

    # Operations by entity type
    entity_types = set(op.entity_type for op in plan.operations)

    for entity_type in sorted(entity_types):
        ops = plan.get_by_entity_type(entity_type)
        if ops:
            console.print(f"\n[bold]{entity_type.title()}:[/bold]")
            for op in ops[:10]:  # Show first 10
                icon = "+" if op.operation == "create" else "~" if op.operation == "update" else "-" if op.operation == "delete" else "↑"
                color = "green" if op.operation == "create" else "yellow" if op.operation == "update" else "red" if op.operation == "delete" else "cyan"
                console.print(f" [{color}]{icon}[/{color}] {op.description}")

            if len(ops) > 10:
                console.print(f" [dim]... and {len(ops) - 10} more[/dim]")

    console.print(f"\n[bold]Total operations:[/bold] {plan.total_operations}")

    if plan.has_conflicts:
        console.print(f"[yellow]Conflicts:[/yellow] {len(plan.conflicts)}")


def _display_results(result: dict, dry_run: bool = False):
    """Display sync execution results"""
    if dry_run:
        console.print("\n[bold cyan]Dry run complete[/bold cyan]")
        console.print(f"Would execute: {result['would_execute']} operations")
        return

    console.print(f"\n[bold]Sync Results:[/bold]")
    console.print(f"  Total: {result['total_operations']}")
    console.print(f"  [green]Successful:[/green] {result['successful']}")

    if result['failed'] > 0:
        console.print(f"  [red]Failed:[/red] {result['failed']}")

        if result.get('errors'):
            console.print("\n[red]Errors:[/red]")
            for error in result['errors']:
                console.print(f"  - {error['operation']}: {error['error']}")


if __name__ == "__main__":
    app()
