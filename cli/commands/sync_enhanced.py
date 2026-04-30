"""
Enhanced Sync Commands for Story #422: Sync Apply Command

Additional helper functions for sync apply with:
- Enhanced confirmation prompts
- Sync history tracking
- Progress display
- Plan ID loading
"""
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

try:
    from ..sync_planner import SyncPlan
    from ..config import CONFIG_DIR
except ImportError:
    from sync_planner import SyncPlan
    from config import CONFIG_DIR

console = Console()
SYNC_HISTORY_FILE = Path(CONFIG_DIR) / "sync_history.json"


def show_confirmation_prompt(plan: SyncPlan, direction: str):
    """
    Show enhanced confirmation prompt with detailed summary

    Args:
        plan: SyncPlan to display
        direction: Sync direction (push/pull/bidirectional)
    """
    summary = plan.get_summary()

    # Count by entity type
    entity_counts = {}
    for op in plan.operations:
        entity_counts[op.entity_type] = entity_counts.get(op.entity_type, 0) + 1

    # Estimate data size (simplified - would need actual data for real estimate)
    estimated_size_mb = len(plan.operations) * 0.5  # ~500KB per operation estimate
    estimated_time_secs = len(plan.operations) * 2   # ~2 seconds per operation estimate

    # Build confirmation message
    console.print("\n[bold cyan]About to sync:[/bold cyan]")

    for entity_type, count in sorted(entity_counts.items()):
        console.print(f"  - {count:,} {entity_type} ({direction})")

    console.print(f"\n[dim]Estimated time: {_format_duration(estimated_time_secs)}[/dim]")
    console.print(f"[dim]Estimated size: {estimated_size_mb:.1f} MB[/dim]")

    if plan.has_conflicts:
        console.print(f"\n[yellow]⚠️  Warning: {len(plan.conflicts)} conflict(s) detected[/yellow]")


def save_sync_history(plan: SyncPlan, result: Dict[str, Any], execution_time: float, direction: str):
    """
    Save sync execution to history file

    Args:
        plan: Executed SyncPlan
        result: Execution result
        execution_time: Time taken in seconds
        direction: Sync direction
    """
    # Ensure config directory exists
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    # Load existing history
    history = []
    if SYNC_HISTORY_FILE.exists():
        try:
            with open(SYNC_HISTORY_FILE, 'r') as f:
                history = json.load(f)
        except (json.JSONDecodeError, IOError):
            history = []

    # Create history entry
    sync_id = result.get('sync_id', f"sync_{int(time.time())}")
    entry = {
        'sync_id': sync_id,
        'timestamp': datetime.utcnow().isoformat(),
        'direction': direction,
        'status': result.get('status', 'unknown'),
        'total_operations': result.get('total_operations', 0),
        'successful': result.get('successful', 0),
        'failed': result.get('failed', 0),
        'execution_time_seconds': round(execution_time, 2),
        'has_conflicts': plan.has_conflicts,
        'errors': result.get('errors', [])[:5]  # Keep only first 5 errors
    }

    # Add to history (keep last 100 entries)
    history.insert(0, entry)
    history = history[:100]

    # Save
    with open(SYNC_HISTORY_FILE, 'w') as f:
        json.dump(history, f, indent=2)

    console.print(f"[dim]Sync history saved to {SYNC_HISTORY_FILE}[/dim]")


def load_plan_by_id(plan_id: str) -> Optional[SyncPlan]:
    """
    Load a sync plan by ID from history

    Args:
        plan_id: Plan ID to load

    Returns:
        SyncPlan if found, None otherwise
    """
    # In a real implementation, this would load saved plans
    # For now, return None (plans are generated on-demand)
    console.print(f"[yellow]Note:[/yellow] Plan loading from history not yet implemented")
    console.print("Generating new plan instead...")
    return None


def display_results_enhanced(result: Dict[str, Any], dry_run: bool, execution_time: float):
    """
    Display enhanced sync execution results with statistics

    Args:
        result: Execution result
        dry_run: Whether this was a dry run
        execution_time: Time taken in seconds
    """
    if dry_run:
        console.print("\n[bold cyan]🔍 Dry Run - No changes made[/bold cyan]")
        console.print(f"Would execute: {result.get('would_execute', 0)} operations")
        summary = result.get('summary', {})
        if summary:
            table = Table(title="Would Execute")
            table.add_column("Operation", style="cyan")
            table.add_column("Count", style="magenta", justify="right")

            for op_type, count in summary.items():
                if op_type != 'total' and count > 0:
                    table.add_row(op_type.title(), str(count))

            console.print(table)
        return

    # Success or failure status
    status = result.get('status', 'unknown')
    if status == 'success':
        console.print("\n[bold green]✅ Sync completed successfully[/bold green]")
    elif status == 'failed':
        console.print("\n[bold red]❌ Sync failed[/bold red]")
    elif status == 'cancelled':
        console.print("\n[bold yellow]⚠️  Sync cancelled[/bold yellow]")

    # Statistics table
    table = Table(title="Sync Statistics")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="magenta", justify="right")

    table.add_row("Total operations", f"{result.get('total_operations', 0):,}")
    table.add_row("Successful", f"[green]{result.get('successful', 0):,}[/green]")

    if result.get('failed', 0) > 0:
        table.add_row("Failed", f"[red]{result.get('failed', 0):,}[/red]")

    table.add_row("Execution time", _format_duration(execution_time))

    # Calculate throughput
    if execution_time > 0:
        ops_per_sec = result.get('successful', 0) / execution_time
        table.add_row("Operations/sec", f"{ops_per_sec:.1f}")

    console.print(table)

    # Display errors if any
    errors = result.get('errors', [])
    if errors:
        console.print("\n[bold red]Errors:[/bold red]")
        for i, error in enumerate(errors[:10], 1):  # Show first 10
            console.print(f"  {i}. {error.get('operation', 'Unknown')}: {error.get('error', 'No details')}")

        if len(errors) > 10:
            console.print(f"  [dim]... and {len(errors) - 10} more errors[/dim]")


def _format_duration(seconds: float) -> str:
    """
    Format duration in human-readable format

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted string (e.g., "2m 30s")
    """
    if seconds < 60:
        return f"{int(seconds)}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"


def display_plan_enhanced(plan: SyncPlan, direction: str):
    """
    Display enhanced sync plan with all details

    Args:
        plan: SyncPlan to display
        direction: Sync direction
    """
    console.print(f"\n[bold cyan]📋 Sync Plan ({direction.upper()})[/bold cyan]\n")

    summary = plan.get_summary()

    # Summary panel
    summary_text = []
    for op_type, count in summary.items():
        if op_type != 'total' and count > 0:
            icon = "+" if op_type == "create" else "~" if op_type == "update" else "-" if op_type == "delete" else "↑"
            summary_text.append(f"{icon} {op_type.title()}: {count}")

    if summary_text:
        panel = Panel(
            "\n".join(summary_text),
            title="[bold]Operations Summary[/bold]",
            border_style="cyan"
        )
        console.print(panel)

    # Entity breakdown
    entity_counts = {}
    for op in plan.operations:
        key = (op.entity_type, op.operation)
        entity_counts[key] = entity_counts.get(key, 0) + 1

    if entity_counts:
        console.print("\n[bold]Entity Breakdown:[/bold]")
        table = Table()
        table.add_column("Entity Type", style="cyan")
        table.add_column("Operation", style="yellow")
        table.add_column("Count", style="magenta", justify="right")

        for (entity_type, operation), count in sorted(entity_counts.items()):
            table.add_row(entity_type.title(), operation.title(), str(count))

        console.print(table)

    # Conflicts
    if plan.has_conflicts:
        console.print(f"\n[yellow]⚠️  Conflicts detected: {len(plan.conflicts)}[/yellow]")
        console.print("[dim]Use --strategy to specify conflict resolution[/dim]")

    console.print(f"\n[bold]Total operations:[/bold] {plan.total_operations}")
