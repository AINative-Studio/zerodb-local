"""
Local Environment Commands - Manage local Docker environment

Story 3.2: Local Environment Commands
"""
import typer
import subprocess
import shutil
from pathlib import Path
from typing import Optional, List
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

app = typer.Typer(help="Manage local ZeroDB environment")
console = Console()

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()
DOCKER_COMPOSE_FILE = PROJECT_ROOT / "docker-compose.yml"
DATA_DIR = PROJECT_ROOT / "data"


def check_docker_installed() -> bool:
    """Check if Docker is installed and running"""
    try:
        result = subprocess.run(
            ["docker", "version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def run_docker_compose(args: List[str], check: bool = True, capture_output: bool = True) -> subprocess.CompletedProcess:
    """
    Execute docker-compose command

    Args:
        args: Command arguments (e.g., ['up', '-d'])
        check: Raise exception on non-zero exit code
        capture_output: Capture stdout/stderr

    Returns:
        CompletedProcess instance
    """
    cmd = ["docker-compose", "-f", str(DOCKER_COMPOSE_FILE)] + args

    try:
        result = subprocess.run(
            cmd,
            cwd=str(PROJECT_ROOT),
            capture_output=capture_output,
            text=True,
            check=check
        )
        return result
    except FileNotFoundError:
        console.print("[red]Error:[/red] Docker Compose not found. Please install Docker Desktop.")
        raise typer.Exit(1)
    except subprocess.CalledProcessError as e:
        console.print(f"[red]Error:[/red] Docker command failed: {e.stderr}")
        raise typer.Exit(1)


@app.command("init")
def local_init():
    """Initialize local ZeroDB environment"""
    console.print("[cyan]Initializing local environment...[/cyan]")

    # Check Docker
    if not check_docker_installed():
        console.print("[red]Error:[/red] Docker is not installed or not running")
        console.print("Please install Docker Desktop: https://www.docker.com/products/docker-desktop")
        raise typer.Exit(1)

    # Create data directories
    console.print("Creating data directories...")
    (DATA_DIR / "postgres").mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "qdrant").mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "minio").mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "redpanda").mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "embeddings/models").mkdir(parents=True, exist_ok=True)

    console.print("[green]✓[/green] Local environment initialized")
    console.print("\nRun '[cyan]zerodb local up[/cyan]' to start services")


@app.command("up")
def local_up(
    detach: bool = typer.Option(True, "--detach", "-d", help="Run in background"),
    logs: bool = typer.Option(False, "--logs", "-l", help="Show logs")
):
    """Start all services"""
    console.print("[cyan]Starting services...[/cyan]")

    if not check_docker_installed():
        console.print("[red]Error:[/red] Docker is not installed or not running")
        raise typer.Exit(1)

    # Build command
    args = ["up"]
    if detach and not logs:
        args.append("-d")
    if logs:
        args.append("--attach")

    try:
        # Start services
        result = run_docker_compose(args, capture_output=not logs)

        if detach and not logs:
            console.print("[green]✓[/green] Services started successfully")
            console.print("\nRun '[cyan]zerodb local status[/cyan]' to check service health")
            console.print("Run '[cyan]zerodb local logs[/cyan]' to view logs")

    except subprocess.CalledProcessError as e:
        console.print(f"[red]Failed to start services[/red]")
        raise typer.Exit(1)


@app.command("down")
def local_down(
    volumes: bool = typer.Option(False, "--volumes", "-v", help="Remove volumes")
):
    """Stop all services"""
    console.print("[cyan]Stopping services...[/cyan]")

    if not check_docker_installed():
        console.print("[red]Error:[/red] Docker is not installed or not running")
        raise typer.Exit(1)

    args = ["down"]
    if volumes:
        args.append("-v")

    try:
        run_docker_compose(args)
        console.print("[green]✓[/green] Services stopped successfully")

        if volumes:
            console.print("[yellow]⚠[/yellow]  Volumes removed")
    except subprocess.CalledProcessError:
        console.print("[red]Failed to stop services[/red]")
        raise typer.Exit(1)


@app.command("status")
def local_status():
    """Show service status and health"""
    console.print("[cyan]Checking service status...[/cyan]\n")

    if not check_docker_installed():
        console.print("[red]Error:[/red] Docker is not installed or not running")
        raise typer.Exit(1)

    try:
        # Get service status
        result = run_docker_compose(["ps", "--format", "table"])

        if result.stdout:
            # Parse and display with colors
            lines = result.stdout.strip().split('\n')

            if len(lines) > 1:
                # Create Rich table
                table = Table(title="ZeroDB Local Services")
                table.add_column("Service", style="cyan")
                table.add_column("Status", style="white")
                table.add_column("Health", style="white")
                table.add_column("Ports", style="dim")

                # Parse output (skip header)
                for line in lines[1:]:
                    parts = line.split()
                    if len(parts) >= 2:
                        name = parts[0].replace('zerodb-', '')
                        status = parts[1] if len(parts) > 1 else 'unknown'

                        # Determine health color
                        if 'running' in status.lower():
                            status_color = "[green]running[/green]"
                        elif 'exited' in status.lower():
                            status_color = "[red]stopped[/red]"
                        else:
                            status_color = f"[yellow]{status}[/yellow]"

                        # Extract health if available
                        health = "N/A"
                        health_color = "[dim]N/A[/dim]"
                        if 'healthy' in line.lower():
                            health = "healthy"
                            health_color = "[green]healthy[/green]"
                        elif 'unhealthy' in line.lower():
                            health = "unhealthy"
                            health_color = "[red]unhealthy[/red]"
                        elif 'starting' in line.lower():
                            health = "starting"
                            health_color = "[yellow]starting[/yellow]"

                        # Extract ports
                        ports = ""
                        if '->' in line:
                            port_parts = line.split('->')
                            if len(port_parts) > 1:
                                ports = port_parts[0].split()[-1] + '->' + port_parts[1].split()[0]

                        table.add_row(name, status_color, health_color, ports)

                console.print(table)
            else:
                console.print("[yellow]No services running[/yellow]")
                console.print("\nRun '[cyan]zerodb local up[/cyan]' to start services")
        else:
            console.print("[yellow]No services running[/yellow]")

    except subprocess.CalledProcessError:
        console.print("[red]Failed to get service status[/red]")
        raise typer.Exit(1)


@app.command("logs")
def local_logs(
    service: Optional[str] = typer.Argument(None, help="Service name (e.g., zerodb-api, postgres)"),
    follow: bool = typer.Option(True, "--follow/--no-follow", "-f/-F", help="Follow log output")
):
    """View service logs"""

    if not check_docker_installed():
        console.print("[red]Error:[/red] Docker is not installed or not running")
        raise typer.Exit(1)

    service_msg = f" for {service}" if service else " (all services)"
    console.print(f"[cyan]Viewing logs{service_msg}...[/cyan]")
    console.print("[dim]Press Ctrl+C to stop[/dim]\n")

    args = ["logs"]
    if follow:
        args.append("-f")
    if service:
        args.append(service)

    try:
        # Run without capturing output so logs stream to terminal
        run_docker_compose(args, capture_output=False, check=False)
    except KeyboardInterrupt:
        console.print("\n[yellow]Stopped viewing logs[/yellow]")


@app.command("restart")
def local_restart(
    service: Optional[str] = typer.Option(None, "--service", "-s", help="Restart specific service")
):
    """Restart services"""

    if not check_docker_installed():
        console.print("[red]Error:[/red] Docker is not installed or not running")
        raise typer.Exit(1)

    service_msg = f" {service}" if service else " all services"
    console.print(f"[cyan]Restarting{service_msg}...[/cyan]")

    args = ["restart"]
    if service:
        args.append(service)

    try:
        run_docker_compose(args)
        console.print(f"[green]✓[/green] Restarted{service_msg} successfully")
    except subprocess.CalledProcessError:
        console.print(f"[red]Failed to restart{service_msg}[/red]")
        raise typer.Exit(1)


@app.command("reset")
def local_reset(
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation")
):
    """Reset environment (stop services, remove volumes and data)"""

    if not check_docker_installed():
        console.print("[red]Error:[/red] Docker is not installed or not running")
        raise typer.Exit(1)

    console.print("[yellow]⚠ WARNING:[/yellow] This will:")
    console.print("  - Stop all services")
    console.print("  - Remove all volumes")
    console.print("  - Delete all data in data/ directory")
    console.print("  - Reset environment to fresh state\n")

    if not yes:
        confirmed = typer.confirm("Are you sure you want to reset the environment?")
        if not confirmed:
            console.print("[yellow]Reset cancelled[/yellow]")
            return

    console.print("[cyan]Resetting environment...[/cyan]")

    try:
        # Stop services and remove volumes
        console.print("Stopping services...")
        run_docker_compose(["down", "-v"])

        # Remove data directory contents
        if DATA_DIR.exists():
            console.print("Removing data directory...")
            shutil.rmtree(DATA_DIR)
            DATA_DIR.mkdir(parents=True, exist_ok=True)

        console.print("[green]✓[/green] Environment reset successfully")
        console.print("\nRun '[cyan]zerodb local init[/cyan]' to reinitialize")

    except subprocess.CalledProcessError:
        console.print("[red]Failed to reset environment[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
