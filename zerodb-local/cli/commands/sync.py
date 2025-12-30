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
    direction: str = typer.Option("bidirectional", "--direction", "-d", help="Sync direction: push, pull, bidirectional"),
    entity_types: Optional[str] = typer.Option(None, "--entity-types", help="Comma-separated entity types (vectors,tables,files,events,memory)"),
    format: str = typer.Option("table", "--format", "-f", help="Output format: table, json"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview without connecting to cloud"),
):
    """
    Generate and display sync plan showing differences between local and cloud

    Story #421: Sync Plan Command

    Shows what would be synced including:
    - Summary statistics by entity type
    - Estimated data size and time
    - Conflicts and schema changes
    - Detailed entity breakdown

    Examples:
        zerodb sync plan
        zerodb sync plan --direction push
        zerodb sync plan --direction pull
        zerodb sync plan --entity-types vectors,tables
        zerodb sync plan --format json
        zerodb sync plan --dry-run
    """
    try:
        # Validate direction
        valid_directions = ['push', 'pull', 'bidirectional']
        if direction not in valid_directions:
            console.print(f"[red]Error:[/red] Invalid direction '{direction}'. Must be one of: {', '.join(valid_directions)}")
            raise typer.Exit(1)

        # Validate format
        valid_formats = ['table', 'json']
        if format not in valid_formats:
            console.print(f"[red]Error:[/red] Invalid format '{format}'. Must be one of: {', '.join(valid_formats)}")
            raise typer.Exit(1)

        # Load configuration
        config = load_config()
        project_id = config.get('project_id')
        cloud_api_url = config.get('cloud_api_url', 'https://api.ainative.studio')
        local_api_url = config.get('local_api_url', 'http://localhost:8000')

        # Check for project linkage
        if not project_id:
            console.print("[red]Error:[/red] No project linked. Run 'zerodb cloud link <project_id>' first.")
            raise typer.Exit(1)

        # Check for cloud credentials (unless dry-run)
        if not dry_run:
            credentials = get_cloud_credentials()
            if not credentials:
                console.print("[red]Error:[/red] Authentication failed. Run 'zerodb cloud login' first.")
                raise typer.Exit(1)

        # Parse entity types filter
        filters = None
        if entity_types:
            entity_list = [e.strip() for e in entity_types.split(',')]
            valid_entities = ['vectors', 'tables', 'files', 'events', 'memory']
            invalid = [e for e in entity_list if e not in valid_entities]
            if invalid:
                console.print(f"[red]Error:[/red] Invalid entity types: {', '.join(invalid)}")
                console.print(f"Valid types: {', '.join(valid_entities)}")
                raise typer.Exit(1)
            filters = {'entities': entity_list}

        # Create planner
        planner = SyncPlanner(local_api_url=local_api_url, cloud_api_url=cloud_api_url)

        # Dry run mode - show what would be checked
        if dry_run:
            console.print(f"[dim]Dry run mode - preview without cloud connection[/dim]\n")
            console.print(f"[cyan]Would check sync plan for:[/cyan]")
            console.print(f"  Project ID: {project_id}")
            console.print(f"  Direction: {direction}")
            console.print(f"  Local API: {local_api_url}")
            console.print(f"  Cloud API: {cloud_api_url}")
            if filters:
                console.print(f"  Entity types: {', '.join(filters['entities'])}")
            console.print("\n[yellow]Note:[/yellow] Use without --dry-run to generate actual sync plan")
            return

        # Generate plan
        entity_filter_str = f" ({', '.join(filters['entities'])})" if filters else ""
        console.print(f"[cyan]Generating sync plan for project {project_id}{entity_filter_str}...[/cyan]")

        try:
            plan = planner.generate_plan(
                project_id=project_id,
                direction=direction,
                mode='incremental',
                filters=filters
            )
        except ConnectionError as e:
            console.print(f"[red]Error:[/red] Cannot connect to cloud. Check CLOUD_API_URL: {cloud_api_url}")
            console.print(f"Details: {str(e)}")
            raise typer.Exit(1)
        except Exception as e:
            console.print(f"[red]Error:[/red] Failed to generate sync plan: {str(e)}")
            raise typer.Exit(1)

        # Output based on format
        if format == 'json':
            console.print(planner.plan_to_json(plan))
        else:
            _display_plan_enhanced(plan, direction)

    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {str(e)}")
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


def _display_plan_enhanced(plan: SyncPlan, direction: str):
    """
    Display sync plan with enhanced formatting and detailed statistics

    Shows:
    - Summary table with entity types and operations
    - Estimated data size
    - Conflicts and schema changes
    - Detailed breakdown by entity type
    """
    console.print(f"\n[bold cyan]Sync Plan[/bold cyan]")
    console.print(f"[dim]Direction: {direction.upper()} | Mode: {plan.mode} | Created: {plan.created_at[:19]}[/dim]\n")

    # Calculate statistics by entity type
    entity_stats = {}
    for op in plan.operations:
        if op.entity_type not in entity_stats:
            entity_stats[op.entity_type] = {
                'count': 0,
                'operations': [],
                'estimated_size': 0
            }
        entity_stats[op.entity_type]['count'] += 1
        entity_stats[op.entity_type]['operations'].append(op.operation)

        # Estimate size (placeholder - real implementation would calculate actual sizes)
        if op.entity_type == 'vectors':
            entity_stats[op.entity_type]['estimated_size'] += 4096  # ~4KB per vector
        elif op.entity_type == 'tables':
            entity_stats[op.entity_type]['estimated_size'] += 1024  # ~1KB per row estimate
        elif op.entity_type == 'files':
            entity_stats[op.entity_type]['estimated_size'] += 8192  # ~8KB per file estimate

    # Main summary table
    if entity_stats:
        table = Table(
            title="Sync Plan Summary",
            show_header=True,
            header_style="bold cyan",
            border_style="cyan"
        )
        table.add_column("Entity Type", style="cyan", no_wrap=True)
        table.add_column("Operation", style="yellow", no_wrap=True)
        table.add_column("Count", justify="right", style="magenta")
        table.add_column("Est. Size", justify="right", style="green")

        for entity_type, stats in sorted(entity_stats.items()):
            # Determine primary operation
            ops_count = {}
            for op in stats['operations']:
                ops_count[op] = ops_count.get(op, 0) + 1
            primary_op = max(ops_count.items(), key=lambda x: x[1])[0].title()

            # Format size
            size_bytes = stats['estimated_size']
            if size_bytes < 1024:
                size_str = f"{size_bytes} B"
            elif size_bytes < 1024 * 1024:
                size_str = f"{size_bytes / 1024:.1f} KB"
            else:
                size_str = f"{size_bytes / (1024 * 1024):.1f} MB"

            # Format count
            count_str = f"{stats['count']:,}"
            if entity_type == 'tables':
                count_str = f"{stats['count']} table{'s' if stats['count'] != 1 else ''}"
            elif entity_type == 'files':
                count_str = f"{stats['count']} file{'s' if stats['count'] != 1 else ''}"

            table.add_row(
                entity_type.title(),
                primary_op,
                count_str,
                size_str
            )

        console.print(table)
    else:
        console.print("[green]No changes to sync. Everything is up to date.[/green]")
        return

    # Totals
    total_size = sum(s['estimated_size'] for s in entity_stats.values())
    if total_size < 1024:
        total_size_str = f"{total_size} B"
    elif total_size < 1024 * 1024:
        total_size_str = f"{total_size / 1024:.1f} KB"
    else:
        total_size_str = f"{total_size / (1024 * 1024):.1f} MB"

    console.print(f"\n[bold]Total Operations:[/bold] {plan.total_operations:,}")
    console.print(f"[bold]Total Estimated Size:[/bold] {total_size_str}")

    # Estimate time (rough calculation: ~100KB/sec for network transfer)
    if total_size > 0:
        estimated_seconds = max(1, int(total_size / 102400))  # 100KB/s
        if estimated_seconds < 60:
            time_str = f"{estimated_seconds} second{'s' if estimated_seconds != 1 else ''}"
        else:
            minutes = estimated_seconds // 60
            time_str = f"{minutes} minute{'s' if minutes != 1 else ''}"
        console.print(f"[bold]Estimated Time:[/bold] {time_str}")

    # Conflicts section
    if plan.has_conflicts:
        console.print(f"\n[yellow]⚠️  Conflicts Detected: {len(plan.conflicts)}[/yellow]")

        conflicts_table = Table(show_header=True, header_style="bold yellow", border_style="yellow")
        conflicts_table.add_column("Entity Type", style="cyan")
        conflicts_table.add_column("Entity ID", style="dim")
        conflicts_table.add_column("Issue", style="yellow")

        for conflict in plan.conflicts[:5]:  # Show first 5 conflicts
            conflicts_table.add_row(
                conflict.get('entity_type', 'unknown'),
                conflict.get('entity_id', 'N/A')[:20],
                "Modified in both local and cloud"
            )

        console.print(conflicts_table)

        if len(plan.conflicts) > 5:
            console.print(f"[dim]... and {len(plan.conflicts) - 5} more conflicts[/dim]")

        console.print("\n[yellow]Run 'zerodb sync apply' to resolve conflicts interactively[/yellow]")

    # Breaking changes warning
    schema_changes = [op for op in plan.operations if op.entity_type == 'tables' and op.operation in ['delete', 'update']]
    if schema_changes:
        console.print(f"\n[red]⚠️  Potential Schema Changes: {len(schema_changes)}[/red]")
        console.print("[dim]Review table modifications carefully before applying[/dim]")

    # Detailed breakdown
    console.print(f"\n[bold]Detailed Breakdown:[/bold]")
    for entity_type in sorted(entity_stats.keys()):
        ops = plan.get_by_entity_type(entity_type)
        console.print(f"\n[cyan]{entity_type.title()}:[/cyan] {len(ops)} operation{'s' if len(ops) != 1 else ''}")

        # Group by operation type
        op_groups = {}
        for op in ops:
            if op.operation not in op_groups:
                op_groups[op.operation] = []
            op_groups[op.operation].append(op)

        for op_type, op_list in sorted(op_groups.items()):
            icon = "+" if op_type == "create" else "~" if op_type == "update" else "-" if op_type == "delete" else "↑"
            color = "green" if op_type == "create" else "yellow" if op_type == "update" else "red" if op_type == "delete" else "cyan"

            console.print(f"  [{color}]{icon} {op_type.title()}[/{color}]: {len(op_list)} item{'s' if len(op_list) != 1 else ''}")

            # Show sample items
            for op in op_list[:3]:
                name = op.entity_name or op.entity_id or 'unnamed'
                desc = op.description or f"{op.entity_type} {op.operation}"
                console.print(f"    [{color}]•[/{color}] [dim]{name[:50]}[/dim]")

            if len(op_list) > 3:
                console.print(f"    [dim]... and {len(op_list) - 3} more[/dim]")

    console.print(f"\n[bold]Next Steps:[/bold]")
    console.print("  1. Review the sync plan above")
    console.print("  2. Run 'zerodb sync apply' to execute the sync")
    console.print("  3. Use 'zerodb sync apply --dry-run' to preview without changes")


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
