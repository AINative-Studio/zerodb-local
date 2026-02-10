"""
ZeroDB logs command - View service logs

Stream or view logs from Docker services.

Refs #1132
"""
import typer
import subprocess
from pathlib import Path
from typing import Optional
from rich.console import Console

app = typer.Typer(help="View ZeroDB service logs")
console = Console()

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.resolve()
DOCKER_COMPOSE_FILE = PROJECT_ROOT / "docker-compose.yml"


@app.command()
def logs(
    service: Optional[str] = typer.Argument(None, help="Service name (e.g., postgres, api, dashboard)"),
    follow: bool = typer.Option(True, "--follow/--no-follow", "-f/-F", help="Follow log output"),
    tail: Optional[int] = typer.Option(None, "--tail", "-n", help="Number of lines to show"),
    timestamps: bool = typer.Option(False, "--timestamps", "-t", help="Show timestamps"),
    since: Optional[str] = typer.Option(None, "--since", help="Show logs since (e.g., 1h, 30m)")
):
    """
    View logs from ZeroDB services

    Examples:
        zerodb logs                    # All services, follow mode
        zerodb logs postgres           # Only postgres logs
        zerodb logs --tail 100         # Last 100 lines
        zerodb logs --since 1h         # Logs from last hour
    """
    try:
        service_msg = f" for [cyan]{service}[/cyan]" if service else " (all services)"
        console.print(f"[cyan]Viewing logs{service_msg}...[/cyan]")

        if follow:
            console.print("[dim]Press Ctrl+C to stop[/dim]\n")

        # Build command
        cmd = ["docker-compose", "-f", str(DOCKER_COMPOSE_FILE), "logs"]

        if follow:
            cmd.append("-f")

        if tail:
            cmd.extend(["--tail", str(tail)])

        if timestamps:
            cmd.append("-t")

        if since:
            cmd.extend(["--since", since])

        if service:
            cmd.append(service)

        # Run without capturing output so logs stream to terminal
        subprocess.run(
            cmd,
            cwd=str(PROJECT_ROOT),
            check=False
        )

    except KeyboardInterrupt:
        console.print("\n[yellow]Stopped viewing logs[/yellow]")
    except subprocess.CalledProcessError as e:
        console.print(f"[red]Error viewing logs: {e}[/red]")
        raise typer.Exit(1)
    except FileNotFoundError:
        console.print("[red]Error:[/red] Docker Compose not found")
        console.print("Please install Docker Desktop: https://www.docker.com/products/docker-desktop")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
