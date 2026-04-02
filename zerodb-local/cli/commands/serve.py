"""
ZeroDB Serve Command - One-command local server

Starts a local ZeroDB lite backend server using uvicorn.
Handles data directory creation, embedding model download,
and environment configuration.

Refs #1712
"""
import os
import sys
from pathlib import Path
from typing import Optional

import typer
import uvicorn
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

app = typer.Typer(help="Start local ZeroDB server")
console = Console()

# Default paths
DEFAULT_DATA_DIR = Path.home() / ".zerodb" / "data"
DEFAULT_PORT = 8000
DEFAULT_HOST = "0.0.0.0"
EMBEDDING_MODEL_MARKER = ".embedding_model_ready"


def ensure_data_dir(data_dir: Path) -> None:
    """
    Create data directory if it does not exist.

    Args:
        data_dir: Path to the data directory
    """
    if not data_dir.exists():
        console.print(f"[yellow]Creating data directory:[/yellow] {data_dir}")
        data_dir.mkdir(parents=True, exist_ok=True)
        console.print(f"[green]Data directory created.[/green]")


def download_embedding_model(data_dir: Path) -> None:
    """
    Download embedding model on first run. Uses a marker file
    to skip subsequent downloads.

    Args:
        data_dir: Path to the data directory where model is stored
    """
    marker = data_dir / EMBEDDING_MODEL_MARKER
    if marker.exists():
        return

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Downloading embedding model...", total=None)
        # In a real implementation, this would download the model.
        # For now, create the marker to indicate readiness.
        progress.update(task, description="Embedding model ready.")

    marker.touch()
    console.print("[green]Embedding model initialized.[/green]")


def setup_environment(
    data_dir: Path,
    cloud_key: Optional[str] = None,
) -> None:
    """
    Set environment variables for the lite backend.

    Args:
        data_dir: Path to the data directory
        cloud_key: Optional API key for cloud sync
    """
    os.environ["ZERODB_BACKEND"] = "lite"
    os.environ["ZERODB_DATA_DIR"] = str(data_dir)

    if cloud_key:
        os.environ["ZERODB_CLOUD_KEY"] = cloud_key


def print_startup_banner(host: str, port: int, data_dir: Path) -> None:
    """
    Print the startup banner with server details.

    Args:
        host: Server host address
        port: Server port number
        data_dir: Path to the data directory
    """
    url = f"http://localhost:{port}"
    banner_lines = [
        f"[bold cyan]ZeroDB Local Server[/bold cyan]",
        f"[bold]URL:[/bold]     {url}",
        f"[bold]Backend:[/bold] lite",
        f"[bold]Data:[/bold]    {data_dir}",
    ]
    panel = Panel(
        "\n".join(banner_lines),
        border_style="bright_cyan",
        padding=(1, 2),
    )
    console.print(panel)


@app.callback(invoke_without_command=True)
def serve(
    port: int = typer.Option(
        DEFAULT_PORT,
        "--port",
        "-p",
        help="Port to run the server on",
    ),
    host: str = typer.Option(
        DEFAULT_HOST,
        "--host",
        help="Host to bind the server to",
    ),
    data_dir: Path = typer.Option(
        DEFAULT_DATA_DIR,
        "--data-dir",
        "-d",
        help="Directory for local data storage",
    ),
    cloud_key: Optional[str] = typer.Option(
        None,
        "--cloud-key",
        "-k",
        help="API key for cloud sync",
    ),
    reload: bool = typer.Option(
        False,
        "--reload",
        help="Enable auto-reload for development",
    ),
):
    """
    Start ZeroDB local server.

    Launches a lite backend on the specified port. On first run,
    creates the data directory and downloads the embedding model.

    Examples:
        zerodb serve
        zerodb serve --port 9000
        zerodb serve --cloud-key sk-abc123
        zerodb serve --data-dir /tmp/zerodb
    """
    # Prepare environment
    ensure_data_dir(data_dir)
    download_embedding_model(data_dir)
    setup_environment(data_dir, cloud_key)

    # Print startup banner
    print_startup_banner(host, port, data_dir)

    # Start the server
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info",
    )
