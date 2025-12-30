"""
Inspect Commands - Inspect local database state and environment

Story #423: Add Environment Inspection Commands
"""
import typer
import httpx
import json
import os
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.tree import Tree
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from ..config import load_config, get_project_id
except ImportError:
    from config import load_config, get_project_id

app = typer.Typer(help="Inspect local database state")
console = Console()

# Configuration
LOCAL_API_URL = os.getenv("ZERODB_LOCAL_API_URL", "http://localhost:8000")
API_TIMEOUT = 10.0
MAX_RETRIES = 3


class APIClient:
    """HTTP client for local API with retry logic"""

    def __init__(self, base_url: str = LOCAL_API_URL):
        self.base_url = base_url.rstrip('/')
        self.client = httpx.Client(timeout=API_TIMEOUT)

    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make HTTP request with retry logic"""
        url = f"{self.base_url}{endpoint}"

        for attempt in range(MAX_RETRIES):
            try:
                response = self.client.request(method, url, **kwargs)
                response.raise_for_status()
                return response.json()
            except httpx.ConnectError:
                if attempt == MAX_RETRIES - 1:
                    raise Exception(
                        f"Local API not running at {self.base_url}. "
                        "Run 'zerodb local up' to start the local environment."
                    )
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    raise Exception(f"Resource not found: {endpoint}")
                raise Exception(f"API error: {e.response.status_code} - {e.response.text}")
            except Exception as e:
                if attempt == MAX_RETRIES - 1:
                    raise Exception(f"Request failed: {str(e)}")

    def get(self, endpoint: str, **kwargs) -> Dict[str, Any]:
        """GET request"""
        return self._make_request("GET", endpoint, **kwargs)

    def close(self):
        """Close HTTP client"""
        self.client.close()


def get_current_project_id(project_id: Optional[str] = None) -> str:
    """Get project ID from config or parameter"""
    if project_id:
        return project_id

    config_project_id = get_project_id()
    if not config_project_id:
        console.print("[red]Error:[/red] No project linked. Run 'zerodb cloud link <project_id>' or use --project-id flag.")
        raise typer.Exit(1)

    return config_project_id


def format_bytes(bytes_value: int) -> str:
    """Format bytes to human-readable string"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_value < 1024.0:
            return f"{bytes_value:.2f} {unit}"
        bytes_value /= 1024.0
    return f"{bytes_value:.2f} PB"


def format_timestamp(timestamp: str) -> str:
    """Format ISO timestamp to readable string"""
    try:
        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except:
        return timestamp


def estimate_next_sync(last_sync: Optional[str], changes_count: int) -> str:
    """Estimate next sync time based on change rate"""
    if not last_sync or changes_count == 0:
        return "No pending changes"

    # Simple heuristic: sync when changes > threshold or time elapsed
    if changes_count > 100:
        return "Soon (many changes)"
    elif changes_count > 10:
        return "~5 minutes"
    else:
        return "~15 minutes"


@app.command("sync")
def inspect_sync(
    project_id: Optional[str] = typer.Option(None, "--project-id", "-p", help="Project ID to inspect"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON")
):
    """
    Show sync state for project

    Displays last sync time, direction, entity counts, conflicts, and pending changes.

    Examples:
        zerodb inspect sync
        zerodb inspect sync --project-id abc123
        zerodb inspect sync --json
    """
    try:
        pid = get_current_project_id(project_id)
        client = APIClient()

        # Fetch sync state
        state = client.get(f"/v1/projects/{pid}/sync/state")

        if json_output:
            console.print_json(data=state)
            return

        # Display sync state
        table = Table(title=f"Sync State - Project {pid}")
        table.add_column("Attribute", style="cyan")
        table.add_column("Value", style="magenta")

        table.add_row("Last Sync", format_timestamp(state.get("last_sync_at", "Never")))
        table.add_row("Direction", state.get("direction", "N/A"))
        table.add_row("Status", state.get("status", "Unknown"))
        table.add_row("Pending Changes", str(state.get("pending_changes", 0)))
        table.add_row("Conflicts", str(state.get("conflicts_count", 0)))
        table.add_row("Next Sync", estimate_next_sync(
            state.get("last_sync_at"),
            state.get("pending_changes", 0)
        ))

        console.print(table)

        # Show entity counts if available
        entities = state.get("entity_counts", {})
        if entities:
            console.print("\n[bold]Entity Counts:[/bold]")
            entity_table = Table()
            entity_table.add_column("Entity Type", style="cyan")
            entity_table.add_column("Local", justify="right", style="green")
            entity_table.add_column("Cloud", justify="right", style="blue")
            entity_table.add_column("Delta", justify="right", style="yellow")

            for entity_type, counts in entities.items():
                local = counts.get("local", 0)
                cloud = counts.get("cloud", 0)
                delta = local - cloud
                delta_str = f"+{delta}" if delta > 0 else str(delta)
                entity_table.add_row(entity_type, str(local), str(cloud), delta_str)

            console.print(entity_table)

        client.close()

    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        raise typer.Exit(1)


@app.command("projects")
def inspect_projects(
    json_output: bool = typer.Option(False, "--json", help="Output as JSON")
):
    """
    List all local projects

    Shows project ID, name, creation date, and entity counts.
    Highlights the currently linked project.

    Examples:
        zerodb inspect projects
        zerodb inspect projects --json
    """
    try:
        client = APIClient()
        config = load_config()
        current_project_id = config.get('project_id')

        # Fetch projects
        projects = client.get("/v1/projects")

        if json_output:
            console.print_json(data=projects)
            return

        # Display projects
        table = Table(title="Local Projects")
        table.add_column("Project ID", style="cyan")
        table.add_column("Name", style="magenta")
        table.add_column("Created", style="green")
        table.add_column("Vectors", justify="right", style="blue")
        table.add_column("Tables", justify="right", style="blue")
        table.add_column("Files", justify="right", style="blue")
        table.add_column("Status", style="yellow")

        for project in projects.get("projects", []):
            pid = project.get("id", "N/A")
            name = project.get("name", "Unnamed")
            created = format_timestamp(project.get("created_at", ""))
            vectors = str(project.get("vector_count", 0))
            tables = str(project.get("table_count", 0))
            files = str(project.get("file_count", 0))
            status = "✓ Current" if pid == current_project_id else ""

            table.add_row(pid, name, created, vectors, tables, files, status)

        console.print(table)
        console.print(f"\n[dim]Total: {len(projects.get('projects', []))} project(s)[/dim]")

        client.close()

    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        raise typer.Exit(1)


@app.command("vectors")
def inspect_vectors(
    project_id: Optional[str] = typer.Option(None, "--project-id", "-p", help="Project ID to inspect"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON")
):
    """
    Show vector count and storage statistics

    Displays total vectors, dimensions, storage size, and recent additions.

    Examples:
        zerodb inspect vectors
        zerodb inspect vectors --project-id abc123
        zerodb inspect vectors --json
    """
    try:
        pid = get_current_project_id(project_id)
        client = APIClient()

        # Fetch vector stats
        stats = client.get(f"/v1/projects/{pid}/database/vectors/stats")

        if json_output:
            console.print_json(data=stats)
            return

        # Display stats
        table = Table(title=f"Vector Statistics - Project {pid}")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="magenta")

        table.add_row("Total Vectors", str(stats.get("total_vectors", 0)))
        table.add_row("Dimensions", str(stats.get("dimensions", 1536)))
        table.add_row("Storage Size", format_bytes(stats.get("storage_bytes", 0)))
        table.add_row("Namespaces", str(stats.get("namespace_count", 0)))
        table.add_row("Last Updated", format_timestamp(stats.get("last_updated", "N/A")))

        console.print(table)

        # Show recent additions
        recent = stats.get("recent_additions", [])
        if recent:
            console.print("\n[bold]Recent Additions (Last 10):[/bold]")
            recent_table = Table()
            recent_table.add_column("Vector ID", style="cyan")
            recent_table.add_column("Namespace", style="blue")
            recent_table.add_column("Added", style="green")

            for vector in recent[:10]:
                recent_table.add_row(
                    vector.get("id", "N/A")[:16] + "...",
                    vector.get("namespace", "default"),
                    format_timestamp(vector.get("created_at", ""))
                )

            console.print(recent_table)

        client.close()

    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        raise typer.Exit(1)


@app.command("tables")
def inspect_tables(
    project_id: Optional[str] = typer.Option(None, "--project-id", "-p", help="Project ID to inspect"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON")
):
    """
    List tables and row counts

    Shows all NoSQL tables with row counts, storage size, and last modification time.

    Examples:
        zerodb inspect tables
        zerodb inspect tables --project-id abc123
        zerodb inspect tables --json
    """
    try:
        pid = get_current_project_id(project_id)
        client = APIClient()

        # Fetch tables
        tables_data = client.get(f"/v1/projects/{pid}/database/tables")

        if json_output:
            console.print_json(data=tables_data)
            return

        # Display tables
        table = Table(title=f"Tables - Project {pid}")
        table.add_column("Table Name", style="cyan")
        table.add_column("Row Count", justify="right", style="magenta")
        table.add_column("Size", justify="right", style="blue")
        table.add_column("Last Modified", style="green")

        for tbl in tables_data.get("tables", []):
            table.add_row(
                tbl.get("name", "N/A"),
                str(tbl.get("row_count", 0)),
                format_bytes(tbl.get("size_bytes", 0)),
                format_timestamp(tbl.get("last_modified", "N/A"))
            )

        console.print(table)
        console.print(f"\n[dim]Total: {len(tables_data.get('tables', []))} table(s)[/dim]")

        client.close()

    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        raise typer.Exit(1)


@app.command("files")
def inspect_files(
    project_id: Optional[str] = typer.Option(None, "--project-id", "-p", help="Project ID to inspect"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON")
):
    """
    List files and sizes

    Shows file count, total size, and breakdown by file type.

    Examples:
        zerodb inspect files
        zerodb inspect files --project-id abc123
        zerodb inspect files --json
    """
    try:
        pid = get_current_project_id(project_id)
        client = APIClient()

        # Fetch files
        files_data = client.get(f"/v1/projects/{pid}/database/files")

        if json_output:
            console.print_json(data=files_data)
            return

        # Display summary
        table = Table(title=f"File Storage - Project {pid}")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="magenta")

        total_files = files_data.get("total_files", 0)
        total_size = files_data.get("total_size_bytes", 0)

        table.add_row("Total Files", str(total_files))
        table.add_row("Total Size", format_bytes(total_size))
        table.add_row("Average Size", format_bytes(total_size // total_files if total_files > 0 else 0))

        console.print(table)

        # Show file types breakdown
        file_types = files_data.get("file_types", {})
        if file_types:
            console.print("\n[bold]File Types:[/bold]")
            types_table = Table()
            types_table.add_column("Type", style="cyan")
            types_table.add_column("Count", justify="right", style="magenta")
            types_table.add_column("Size", justify="right", style="blue")
            types_table.add_column("Percentage", justify="right", style="green")

            for file_type, data in sorted(file_types.items(), key=lambda x: x[1].get("count", 0), reverse=True):
                count = data.get("count", 0)
                size = data.get("size_bytes", 0)
                percentage = (count / total_files * 100) if total_files > 0 else 0

                types_table.add_row(
                    file_type or "unknown",
                    str(count),
                    format_bytes(size),
                    f"{percentage:.1f}%"
                )

            console.print(types_table)

        client.close()

    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        raise typer.Exit(1)


@app.command("events")
def inspect_events(
    project_id: Optional[str] = typer.Option(None, "--project-id", "-p", help="Project ID to inspect"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON")
):
    """
    Show event count and latest events

    Displays total event count, event types breakdown, and the 5 most recent events.

    Examples:
        zerodb inspect events
        zerodb inspect events --project-id abc123
        zerodb inspect events --json
    """
    try:
        pid = get_current_project_id(project_id)
        client = APIClient()

        # Fetch events
        events_data = client.get(f"/v1/projects/{pid}/database/events")

        if json_output:
            console.print_json(data=events_data)
            return

        # Display summary
        table = Table(title=f"Event Stream - Project {pid}")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="magenta")

        table.add_row("Total Events", str(events_data.get("total_events", 0)))
        table.add_row("Event Types", str(len(events_data.get("event_types", {}))))
        table.add_row("Oldest Event", format_timestamp(events_data.get("oldest_event", "N/A")))
        table.add_row("Newest Event", format_timestamp(events_data.get("newest_event", "N/A")))

        console.print(table)

        # Show event types breakdown
        event_types = events_data.get("event_types", {})
        if event_types:
            console.print("\n[bold]Event Types:[/bold]")
            types_table = Table()
            types_table.add_column("Event Type", style="cyan")
            types_table.add_column("Count", justify="right", style="magenta")
            types_table.add_column("Percentage", justify="right", style="green")

            total = sum(event_types.values())
            for event_type, count in sorted(event_types.items(), key=lambda x: x[1], reverse=True):
                percentage = (count / total * 100) if total > 0 else 0
                types_table.add_row(event_type, str(count), f"{percentage:.1f}%")

            console.print(types_table)

        # Show latest events
        latest = events_data.get("latest_events", [])
        if latest:
            console.print("\n[bold]Latest Events (Last 5):[/bold]")
            latest_table = Table()
            latest_table.add_column("Timestamp", style="green")
            latest_table.add_column("Type", style="cyan")
            latest_table.add_column("Source", style="blue")
            latest_table.add_column("Description", style="magenta")

            for event in latest[:5]:
                latest_table.add_row(
                    format_timestamp(event.get("timestamp", "")),
                    event.get("type", "N/A"),
                    event.get("source", "N/A"),
                    event.get("description", "")[:50] + "..." if len(event.get("description", "")) > 50 else event.get("description", "")
                )

            console.print(latest_table)

        client.close()

    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        raise typer.Exit(1)


@app.command("health")
def inspect_health(
    json_output: bool = typer.Option(False, "--json", help="Output as JSON")
):
    """
    Overall system health check

    Shows status of all local services: PostgreSQL, Qdrant, MinIO, RedPanda, and Embeddings.
    Color-coded: Green (healthy), Yellow (degraded), Red (down).

    Examples:
        zerodb inspect health
        zerodb inspect health --json
    """
    try:
        client = APIClient()

        # Fetch health status
        health = client.get("/health")

        if json_output:
            console.print_json(data=health)
            return

        # Determine overall status
        overall_status = health.get("status", "unknown")
        status_color = "green" if overall_status == "healthy" else "yellow" if overall_status == "degraded" else "red"
        status_icon = "✅" if overall_status == "healthy" else "⚠️" if overall_status == "degraded" else "❌"

        console.print(f"\n[bold]System Health:[/bold] [{status_color}]{status_icon} {overall_status.title()}[/{status_color}]\n")

        # Display service statuses
        table = Table()
        table.add_column("Service", style="cyan")
        table.add_column("Status", style="bold")
        table.add_column("Response Time", justify="right", style="blue")
        table.add_column("Details", style="dim")

        services = health.get("services", {})
        for service_name, service_data in services.items():
            status = service_data.get("status", "unknown")

            # Determine icon and color
            if status == "healthy":
                icon = "✅"
                color = "green"
            elif status == "degraded":
                icon = "⚠️"
                color = "yellow"
            else:
                icon = "❌"
                color = "red"

            response_time = service_data.get("response_time_ms", 0)
            details = service_data.get("details", "")

            table.add_row(
                service_name.title(),
                f"[{color}]{icon}[/{color}]",
                f"{response_time}ms" if response_time else "N/A",
                details
            )

        console.print(table)

        # Show timestamp
        console.print(f"\n[dim]Last checked: {format_timestamp(health.get('timestamp', datetime.now().isoformat()))}[/dim]")

        client.close()

    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
