"""
ZeroDB status command - Check service health and status

Shows status of all Docker services, health checks, and resource usage.

Refs #1132
"""
import typer
import subprocess
import json as json_lib
from pathlib import Path
from typing import Optional, Dict, List, Any
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from zerodb.utils.prerequisites import check_docker_installed

app = typer.Typer(help="Check ZeroDB service status")
console = Console()

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.resolve()
DOCKER_COMPOSE_FILE = PROJECT_ROOT / "docker-compose.yml"


def parse_docker_compose_output(output: str) -> List[Dict[str, Any]]:
    """
    Parse `docker compose ps --format json` output (newline-delimited JSON,
    one object per container -- not a single JSON array).

    Previously parsed plain-text `docker-compose ps` by splitting each line
    on whitespace and taking the second token as "status" -- correct for
    Compose V1's old column order, but Compose V2 (the version this
    project's docker-compose.yml and README both target) puts IMAGE second
    and STATUS fifth ("Up 21 minutes (healthy)", itself multiple
    whitespace-separated words). That silently took the image name
    (e.g. "zl-fullmode-zerodb-api") as every service's status, which in
    turn made every "'running' in status.lower()" check below always
    false -- confirmed live against a real, fully-healthy 7-service stack,
    which `zerodb status status` reported as "0 of 7 services running".
    JSON output sidesteps column-order parsing entirely.

    Args:
        output: Raw output from `docker compose ps --format json`

    Returns:
        list: Parsed service information
    """
    services = []

    for line in output.strip().split('\n'):
        if not line.strip():
            continue
        try:
            container = json_lib.loads(line)
        except json_lib.JSONDecodeError:
            continue

        name = container.get('Service') or container.get('Name', '').replace('zerodb-', '')
        status = container.get('Status', 'unknown')
        health = (container.get('Health') or 'N/A').lower() or 'N/A'
        if health not in ('healthy', 'unhealthy', 'starting'):
            health = 'N/A'

        # Extract the first published host port, if any.
        port = None
        ports = container.get('Ports', '')
        if '->' in ports:
            try:
                port = int(ports.split('->')[0].split(':')[-1])
            except (ValueError, IndexError):
                pass

        services.append({
            'name': name,
            'status': status,
            'health': health,
            'port': port,
            'state': container.get('State', ''),
        })

    return services


def get_service_health(service_name: str) -> str:
    """
    Get health status of a specific service

    Args:
        service_name: Name of the service

    Returns:
        str: Health status
    """
    try:
        result = subprocess.run(
            ["docker", "inspect", "--format='{{.State.Health.Status}}'", service_name],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.stdout.strip().strip("'") if result.returncode == 0 else 'N/A'
    except:
        return 'N/A'


def get_service_uptime(service_name: str) -> str:
    """
    Get uptime of a specific service

    Args:
        service_name: Name of the service

    Returns:
        str: Uptime string
    """
    try:
        result = subprocess.run(
            ["docker", "inspect", "--format='{{.State.Status}} since {{.State.StartedAt}}'", service_name],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.stdout.strip().strip("'") if result.returncode == 0 else 'N/A'
    except:
        return 'N/A'


def get_resource_usage() -> Dict[str, Dict[str, str]]:
    """
    Get CPU and memory usage for all services

    Returns:
        dict: Resource usage by service
    """
    try:
        result = subprocess.run(
            ["docker", "stats", "--no-stream", "--format", "{{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}"],
            capture_output=True,
            text=True,
            timeout=10
        )

        usage = {}
        for line in result.stdout.strip().split('\n'):
            if not line.strip():
                continue

            parts = line.split('\t')
            if len(parts) >= 3:
                name = parts[0].replace('zerodb-', '')
                usage[name] = {
                    'cpu': parts[1],
                    'memory': parts[2].split('/')[0].strip()
                }

        return usage
    except:
        return {}


def get_all_services_status() -> Dict[str, Any]:
    """
    Get status of all services

    Returns:
        dict: All services status
    """
    try:
        result = subprocess.run(
            ["docker-compose", "-f", str(DOCKER_COMPOSE_FILE), "ps", "--format", "json"],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=str(PROJECT_ROOT)
        )

        services = parse_docker_compose_output(result.stdout)

        return {
            'services': services,
            'total': len(services),
            # Compose's real Status text is "Up 21 minutes (healthy)" --
            # never contains the word "running" -- so this must key off
            # the structured State field ("running"/"exited"/...), not a
            # substring match against Status.
            'running': sum(1 for s in services if s['state'] == 'running')
        }
    except:
        return {'services': [], 'total': 0, 'running': 0}


def get_service_status(service_name: str) -> Dict[str, Any]:
    """
    Get status of a specific service

    Args:
        service_name: Name of the service

    Returns:
        dict: Service status
    """
    try:
        result = subprocess.run(
            ["docker-compose", "-f", str(DOCKER_COMPOSE_FILE), "ps", "--format", "json", service_name],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=str(PROJECT_ROOT)
        )

        services = parse_docker_compose_output(result.stdout)
        return services[0] if services else None
    except:
        return None


@app.command()
def status(
    service: Optional[str] = typer.Argument(None, help="Specific service to check"),
    json: bool = typer.Option(False, "--json", help="Output as JSON"),
    resources: bool = typer.Option(False, "--resources", "-r", help="Show resource usage")
):
    """
    Check status of ZeroDB services
    """
    # Check Docker
    if not check_docker_installed():
        console.print("[red]Error:[/red] Docker is not installed or not running")
        console.print("Please install Docker Desktop: https://www.docker.com/products/docker-desktop")
        raise typer.Exit(1)

    # Get service status
    if service:
        status_data = get_service_status(service)
        if not status_data:
            console.print(f"[red]Service '{service}' not found or not running[/red]")
            raise typer.Exit(1)

        if json:
            console.print(json_lib.dumps(status_data, indent=2))
        else:
            console.print(f"\n[bold]Service: {status_data['name']}[/bold]")
            console.print(f"Status: {status_data['status']}")
            console.print(f"Health: {status_data['health']}")
            if status_data['port']:
                console.print(f"Port: {status_data['port']}")
    else:
        all_status = get_all_services_status()

        if json:
            console.print(json_lib.dumps(all_status, indent=2))
            return

        if not all_status['services']:
            console.print("\n[yellow]No services running[/yellow]")
            console.print("\nRun '[cyan]zerodb init[/cyan]' to set up your environment")
            console.print("Or '[cyan]zerodb local up[/cyan]' to start services")
            return

        # Display table
        table = Table(title="ZeroDB Services Status")
        table.add_column("Service", style="cyan")
        table.add_column("Status", style="white")
        table.add_column("Health", style="white")
        table.add_column("Port", style="dim")

        if resources:
            table.add_column("CPU", style="yellow")
            table.add_column("Memory", style="yellow")

            resource_usage = get_resource_usage()

        for svc in all_status['services']:
            # Status with color, keyed off the structured State field --
            # see parse_docker_compose_output()'s docstring for why a
            # substring match against the free-text Status ("Up 21
            # minutes (healthy)") doesn't work.
            if svc['state'] == 'running':
                status_colored = f"[green]{svc['status']}[/green]"
            elif svc['state'] == 'exited':
                status_colored = f"[red]{svc['status']}[/red]"
            else:
                status_colored = f"[yellow]{svc['status']}[/yellow]"

            # Health with color
            if svc['health'] == 'healthy':
                health_colored = "[green]healthy[/green]"
            elif svc['health'] == 'unhealthy':
                health_colored = "[red]unhealthy[/red]"
            elif svc['health'] == 'starting':
                health_colored = "[yellow]starting[/yellow]"
            else:
                health_colored = "[dim]N/A[/dim]"

            port_str = str(svc['port']) if svc['port'] else ''

            row = [svc['name'], status_colored, health_colored, port_str]

            if resources and svc['name'] in resource_usage:
                usage = resource_usage[svc['name']]
                row.extend([usage['cpu'], usage['memory']])
            elif resources:
                row.extend(['', ''])

            table.add_row(*row)

        console.print()
        console.print(table)
        console.print()

        # Summary
        summary = f"[green]{all_status['running']}[/green] of [cyan]{all_status['total']}[/cyan] services running"
        console.print(Panel(summary, title="Summary", border_style="cyan"))


if __name__ == "__main__":
    app()
