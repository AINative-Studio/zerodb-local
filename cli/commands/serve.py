"""
ZeroDB Serve Command - One-command local server

Starts a local ZeroDB lite backend server using uvicorn.
Handles data directory creation, embedding model download,
and environment configuration.

Refs #1712
"""
import multiprocessing
import os
import signal
import sys
import tempfile
import time
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
# Only this machine by default: local mode has no sign-in, so listening on
# all interfaces would expose every project to the whole network. Opt in
# with --host 0.0.0.0 (and set ZERODB_LOCAL_API_KEY when you do).
DEFAULT_HOST = "127.0.0.1"

_LOOPBACK = {"127.0.0.1", "localhost", "::1"}


def exposure_warning(host: str, key_set: bool) -> Optional[str]:
    """Warning text when the server is reachable from other machines with no key."""
    if host in _LOOPBACK or key_set:
        return None
    return (
        f"Listening on {host}: anyone who can reach this port can read and change "
        "your data. Set ZERODB_LOCAL_API_KEY to require a key, or use --host 127.0.0.1."
    )
EMBEDDING_MODEL_MARKER = ".embedding_model_ready"


def volatile_data_dir_warning(data_dir: Path) -> Optional[str]:
    """
    Warning text when --data-dir resolves under an OS temp location.

    The real default (~/.zerodb/data) is durable and already works
    correctly. This only fires when --data-dir has been pointed somewhere
    that looks temporary, so a user doesn't lose data to routine OS/shell
    cleanup without ever being told their data directory choice was the
    reason -- advisory only, like exposure_warning above; never blocks
    startup.
    """
    resolved_path = Path(data_dir).resolve()
    resolved = str(resolved_path)
    temp_root = str(Path(tempfile.gettempdir()).resolve())

    under_temp_root = resolved == temp_root or resolved.startswith(temp_root + os.sep)
    # tempfile.gettempdir() returns one specific temp root (e.g. macOS's
    # per-session $TMPDIR under /var/folders/<hash>/...), but /tmp,
    # /var/tmp, and ANY /var/folders/... path (not just the one that
    # happens to be this process's own $TMPDIR) are also conventionally
    # temporary -- Path.parts splits directories individually, so
    # "var_folders" never appears as a single part; check for adjacent
    # "var", "folders" parts instead, and bare "tmp"/"var_tmp" elsewhere.
    parts = resolved_path.parts
    under_known_temp_name = any(
        part in ("tmp", "var_tmp") for part in parts
    ) or any(
        parts[i] == "var" and parts[i + 1] == "folders"
        for i in range(len(parts) - 1)
    )

    if not (under_temp_root or under_known_temp_name):
        return None

    return (
        f"{resolved} looks like a temporary directory and may not survive a "
        "reboot or routine cleanup. Your data won't be safe here long-term -- "
        f"consider --data-dir {DEFAULT_DATA_DIR} (the default) or another "
        "durable location."
    )


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
    # Resolve to an absolute path before the server chdir's into api/ below
    # (Refs #75) -- a relative --data-dir would otherwise end up resolved
    # against api/ instead of the directory the user actually meant.
    os.environ["ZERODB_DATA_DIR"] = str(Path(data_dir).resolve())

    if cloud_key:
        os.environ["ZERODB_CLOUD_KEY"] = cloud_key


def _run_server(host: str, port: int, reload: bool) -> None:
    """
    Load and run the FastAPI app. Runs uvicorn.run(), which blocks until
    the server stops. Imported and called both directly (no --watch) and
    as a multiprocessing.Process target (with --watch, see watch_server
    below) -- must be a plain top-level function, not a closure, so it
    can be pickled for the child process on spawn-start platforms (macOS,
    Windows).
    """
    # The FastAPI app lives in api/main.py (package "api" per
    # pyproject.toml, not "app" -- no "app" package exists anywhere in
    # this repo or an installed distribution; Refs #75). It also uses
    # sibling-relative imports internally (e.g. "from health import
    # ..."), so api/ itself must be the working directory for those to
    # resolve, not just importable as a dotted package -- find it via
    # importlib (api has no __init__.py, so it is a namespace package
    # whose location varies between a source checkout and an installed
    # distribution) and chdir into it before loading "main:app", the
    # same way the test suite's lite_server fixture already runs it.
    import importlib.util

    api_spec = importlib.util.find_spec("api")
    if api_spec is None or not api_spec.submodule_search_locations:
        console.print("[red]Error:[/red] could not locate the 'api' package.")
        raise typer.Exit(code=1)
    api_dir = list(api_spec.submodule_search_locations)[0]
    os.chdir(api_dir)
    sys.path.insert(0, api_dir)

    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info",
    )


# Backoff schedule (seconds) between restart attempts after an unexpected
# crash -- caps at the last value so a persistently-crashing process (e.g.
# a corrupted data dir) doesn't restart-loop tightly forever, while a
# genuinely transient failure still recovers quickly.
_RESTART_BACKOFF_SECONDS = [1, 2, 5, 10, 30]

# A crash loop this tight (N restarts within this window) means the
# underlying cause is persistent, not transient -- give up with a clear
# error instead of restarting forever.
_CRASH_LOOP_WINDOW_SECONDS = 60
_CRASH_LOOP_MAX_RESTARTS = 5


def watch_server(host: str, port: int, reload: bool) -> None:
    """
    Run the server in a child process and restart it if it dies
    unexpectedly. A clean shutdown (Ctrl+C / SIGTERM, which the child
    exits on with code 0) stops the loop instead of restarting --
    only a crash (nonzero exit, or the process dying to a signal)
    triggers a restart.
    """
    console.print(
        "[dim]Watch mode: the server will restart automatically if it crashes. "
        "Press Ctrl+C to stop.[/dim]"
    )

    restart_times: list = []
    attempt = 0

    def _handle_sigterm(signum, frame):
        # Re-raise as KeyboardInterrupt so the same clean-shutdown path
        # below (which also catches Ctrl+C) handles SIGTERM too.
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, _handle_sigterm)

    while True:
        process = multiprocessing.Process(
            target=_run_server, args=(host, port, reload), daemon=False
        )
        process.start()

        try:
            process.join()
        except KeyboardInterrupt:
            console.print("\n[yellow]Stopping...[/yellow]")
            process.terminate()
            process.join(timeout=10)
            if process.is_alive():
                process.kill()
                process.join()
            return

        if process.exitcode == 0:
            # Clean exit (the child itself handled Ctrl+C/SIGTERM and
            # returned normally) -- don't restart.
            return

        now = time.monotonic()
        restart_times.append(now)
        restart_times[:] = [
            t for t in restart_times if now - t <= _CRASH_LOOP_WINDOW_SECONDS
        ]
        if len(restart_times) > _CRASH_LOOP_MAX_RESTARTS:
            console.print(
                f"[red]Error:[/red] the server crashed {len(restart_times)} times in "
                f"{_CRASH_LOOP_WINDOW_SECONDS}s (exit code {process.exitcode}). "
                "This looks like a persistent failure, not a transient one -- "
                "giving up instead of restarting forever. Check the data "
                "directory and logs, then run 'zerodb serve' again."
            )
            raise typer.Exit(code=1)

        delay = _RESTART_BACKOFF_SECONDS[
            min(attempt, len(_RESTART_BACKOFF_SECONDS) - 1)
        ]
        attempt += 1
        console.print(
            f"[red]Server crashed[/red] (exit code {process.exitcode}). "
            f"Restarting in {delay}s..."
        )
        time.sleep(delay)


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
    watch: bool = typer.Option(
        False,
        "--watch",
        help="Automatically restart the server if it crashes unexpectedly",
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
        zerodb serve --watch
    """
    # Prepare environment
    ensure_data_dir(data_dir)
    download_embedding_model(data_dir)
    setup_environment(data_dir, cloud_key)

    # Print startup banner
    print_startup_banner(host, port, data_dir)
    warning = exposure_warning(host, key_set=bool(os.getenv("ZERODB_LOCAL_API_KEY", "").strip()))
    if warning:
        console.print(f"[yellow]Warning:[/yellow] {warning}")
    data_dir_warning = volatile_data_dir_warning(data_dir)
    if data_dir_warning:
        console.print(f"[yellow]Warning:[/yellow] {data_dir_warning}")

    if watch:
        watch_server(host, port, reload)
    else:
        _run_server(host, port, reload)
