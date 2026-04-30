"""
Conflict Resolver - Detects and resolves conflicts between local and cloud data
"""
from typing import Dict, List, Any, Optional, Literal
from dataclasses import dataclass
import json
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
import typer

console = Console()


@dataclass
class Conflict:
    """Represents a data conflict between local and cloud"""
    entity_type: str
    entity_id: str
    local_value: Dict[str, Any]
    cloud_value: Dict[str, Any]
    local_timestamp: Optional[str] = None
    cloud_timestamp: Optional[str] = None


class ConflictResolutionStrategy:
    """Available conflict resolution strategies"""
    LOCAL_WINS = "local-wins"
    CLOUD_WINS = "cloud-wins"
    NEWEST_WINS = "newest-wins"
    MANUAL = "manual"


class ConflictResolver:
    """Handles conflict detection and resolution"""

    def __init__(self, default_strategy: str = ConflictResolutionStrategy.MANUAL):
        self.default_strategy = default_strategy
        self.resolved_conflicts: List[Dict[str, Any]] = []

    def detect_conflicts(
        self,
        local_changes: List[Dict[str, Any]],
        cloud_changes: List[Dict[str, Any]]
    ) -> List[Conflict]:
        """
        Detect conflicts between local and cloud changes

        Args:
            local_changes: List of local changes
            cloud_changes: List of cloud changes

        Returns:
            List of Conflict objects
        """
        conflicts = []

        for local_change in local_changes:
            for cloud_change in cloud_changes:
                if self._is_conflicting(local_change, cloud_change):
                    conflicts.append(Conflict(
                        entity_type=local_change.get('entity_type', 'unknown'),
                        entity_id=local_change.get('entity_id', 'unknown'),
                        local_value=local_change.get('data', {}),
                        cloud_value=cloud_change.get('data', {}),
                        local_timestamp=local_change.get('timestamp'),
                        cloud_timestamp=cloud_change.get('timestamp')
                    ))

        return conflicts

    def _is_conflicting(self, local_change: Dict, cloud_change: Dict) -> bool:
        """Check if two changes conflict"""
        return (
            local_change.get('entity_type') == cloud_change.get('entity_type') and
            local_change.get('entity_id') == cloud_change.get('entity_id') and
            local_change.get('data') != cloud_change.get('data')
        )

    def resolve_all(
        self,
        conflicts: List[Conflict],
        strategy: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Resolve all conflicts using the specified strategy

        Args:
            conflicts: List of conflicts to resolve
            strategy: Resolution strategy (overrides default)

        Returns:
            List of resolved values
        """
        if not conflicts:
            return []

        strategy = strategy or self.default_strategy
        resolved = []

        console.print(f"\n[bold yellow]⚠️  Found {len(conflicts)} conflict(s)[/bold yellow]\n")

        for idx, conflict in enumerate(conflicts, 1):
            console.print(f"[bold]Conflict {idx}/{len(conflicts)}[/bold]")
            resolution = self.resolve_conflict(conflict, strategy)
            resolved.append(resolution)
            self.resolved_conflicts.append({
                'conflict': conflict,
                'resolution': resolution,
                'strategy': strategy
            })

        return resolved

    def resolve_conflict(
        self,
        conflict: Conflict,
        strategy: str
    ) -> Dict[str, Any]:
        """
        Resolve a single conflict

        Args:
            conflict: Conflict to resolve
            strategy: Resolution strategy

        Returns:
            Resolved value
        """
        if strategy == ConflictResolutionStrategy.LOCAL_WINS:
            return self._resolve_local_wins(conflict)
        elif strategy == ConflictResolutionStrategy.CLOUD_WINS:
            return self._resolve_cloud_wins(conflict)
        elif strategy == ConflictResolutionStrategy.NEWEST_WINS:
            return self._resolve_newest_wins(conflict)
        elif strategy == ConflictResolutionStrategy.MANUAL:
            return self._resolve_manual(conflict)
        else:
            raise ValueError(f"Unknown resolution strategy: {strategy}")

    def _resolve_local_wins(self, conflict: Conflict) -> Dict[str, Any]:
        """Always use local version"""
        console.print("[green]✓[/green] Using local version (local-wins strategy)")
        return {
            'entity_type': conflict.entity_type,
            'entity_id': conflict.entity_id,
            'data': conflict.local_value,
            'resolution': 'local'
        }

    def _resolve_cloud_wins(self, conflict: Conflict) -> Dict[str, Any]:
        """Always use cloud version"""
        console.print("[blue]✓[/blue] Using cloud version (cloud-wins strategy)")
        return {
            'entity_type': conflict.entity_type,
            'entity_id': conflict.entity_id,
            'data': conflict.cloud_value,
            'resolution': 'cloud'
        }

    def _resolve_newest_wins(self, conflict: Conflict) -> Dict[str, Any]:
        """Use the newest version based on timestamp"""
        if not conflict.local_timestamp or not conflict.cloud_timestamp:
            console.print("[yellow]⚠[/yellow] Missing timestamps, using local version")
            return self._resolve_local_wins(conflict)

        if conflict.local_timestamp > conflict.cloud_timestamp:
            console.print("[green]✓[/green] Using local version (newer)")
            return {
                'entity_type': conflict.entity_type,
                'entity_id': conflict.entity_id,
                'data': conflict.local_value,
                'resolution': 'local'
            }
        else:
            console.print("[blue]✓[/blue] Using cloud version (newer)")
            return {
                'entity_type': conflict.entity_type,
                'entity_id': conflict.entity_id,
                'data': conflict.cloud_value,
                'resolution': 'cloud'
            }

    def _resolve_manual(self, conflict: Conflict) -> Dict[str, Any]:
        """Prompt user to manually resolve the conflict"""
        self._display_conflict(conflict)

        while True:
            console.print("\n[bold]Choose resolution:[/bold]")
            console.print("  [green]1)[/green] Use local version")
            console.print("  [blue]2)[/blue] Use cloud version")
            console.print("  [yellow]3)[/yellow] Merge manually")
            console.print("  [red]4)[/red] Skip this conflict")

            choice = typer.prompt("Enter choice (1-4)", type=int)

            if choice == 1:
                console.print("[green]✓[/green] Using local version")
                return {
                    'entity_type': conflict.entity_type,
                    'entity_id': conflict.entity_id,
                    'data': conflict.local_value,
                    'resolution': 'local'
                }
            elif choice == 2:
                console.print("[blue]✓[/blue] Using cloud version")
                return {
                    'entity_type': conflict.entity_type,
                    'entity_id': conflict.entity_id,
                    'data': conflict.cloud_value,
                    'resolution': 'cloud'
                }
            elif choice == 3:
                merged = self._manual_merge(conflict)
                console.print("[cyan]✓[/cyan] Using merged version")
                return {
                    'entity_type': conflict.entity_type,
                    'entity_id': conflict.entity_id,
                    'data': merged,
                    'resolution': 'merged'
                }
            elif choice == 4:
                console.print("[yellow]⊘[/yellow] Skipping conflict")
                return {
                    'entity_type': conflict.entity_type,
                    'entity_id': conflict.entity_id,
                    'data': None,
                    'resolution': 'skipped'
                }
            else:
                console.print("[red]Invalid choice. Please enter 1-4.[/red]")

    def _display_conflict(self, conflict: Conflict):
        """Display conflict details in a nice format"""
        panel = Panel(
            self._format_conflict_details(conflict),
            title=f"[bold yellow]⚠️  Conflict Detected[/bold yellow]",
            border_style="yellow"
        )
        console.print(panel)

    def _format_conflict_details(self, conflict: Conflict) -> str:
        """Format conflict details for display"""
        details = []
        details.append(f"[bold]Entity Type:[/bold] {conflict.entity_type}")
        details.append(f"[bold]Entity ID:[/bold] {conflict.entity_id}")
        details.append("")
        details.append("[bold green]Local Version:[/bold green]")
        details.append(json.dumps(conflict.local_value, indent=2))
        if conflict.local_timestamp:
            details.append(f"[dim]Updated: {conflict.local_timestamp}[/dim]")
        details.append("")
        details.append("[bold blue]Cloud Version:[/bold blue]")
        details.append(json.dumps(conflict.cloud_value, indent=2))
        if conflict.cloud_timestamp:
            details.append(f"[dim]Updated: {conflict.cloud_timestamp}[/dim]")

        return "\n".join(details)

    def _manual_merge(self, conflict: Conflict) -> Dict[str, Any]:
        """
        Guide user through manual merge

        This shows both versions and lets user build a merged version
        """
        console.print("\n[bold cyan]Manual Merge Mode[/bold cyan]")
        console.print("Choose fields from local or cloud version, or enter custom values.\n")

        # Get all unique keys from both versions
        all_keys = set(conflict.local_value.keys()) | set(conflict.cloud_value.keys())

        merged = {}
        for key in sorted(all_keys):
            local_val = conflict.local_value.get(key, "[not set]")
            cloud_val = conflict.cloud_value.get(key, "[not set]")

            console.print(f"\n[bold]Field: {key}[/bold]")
            console.print(f"  Local: {local_val}")
            console.print(f"  Cloud: {cloud_val}")

            choice = typer.prompt(
                "Use (l)ocal, (c)loud, or (e)nter custom",
                type=str,
                default="l"
            ).lower()

            if choice == 'l':
                merged[key] = local_val
            elif choice == 'c':
                merged[key] = cloud_val
            elif choice == 'e':
                custom = typer.prompt(f"Enter value for {key}")
                merged[key] = custom
            else:
                console.print("[yellow]Invalid choice, using local[/yellow]")
                merged[key] = local_val

        return merged

    def get_summary(self) -> Dict[str, Any]:
        """Get summary of resolved conflicts"""
        total = len(self.resolved_conflicts)
        by_resolution = {}

        for item in self.resolved_conflicts:
            resolution = item['resolution']['resolution']
            by_resolution[resolution] = by_resolution.get(resolution, 0) + 1

        return {
            'total_conflicts': total,
            'by_resolution': by_resolution
        }

    def display_summary(self):
        """Display summary of conflict resolutions"""
        if not self.resolved_conflicts:
            console.print("[green]✓[/green] No conflicts detected")
            return

        summary = self.get_summary()

        table = Table(title="Conflict Resolution Summary")
        table.add_column("Resolution Type", style="cyan")
        table.add_column("Count", style="magenta", justify="right")

        for resolution_type, count in summary['by_resolution'].items():
            table.add_row(resolution_type, str(count))

        console.print(table)
