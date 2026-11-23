"""
ZeroDB Local CLI entry point.

Re-exports the Typer app from the existing CLI module so that
`pip install zerodb-local` exposes the `zerodb` console script.

When the full CLI tree (cli/zerodb_main.py) is not on sys.path
(i.e. installed via pip rather than run from source), a minimal
Typer app is provided with a `serve` command and version output.
"""

import sys
from pathlib import Path

import typer

# ---------------------------------------------------------------------------
# Try to import the full CLI app from the existing cli/ directory.  When
# running from a source checkout the cli/ directory is a sibling of this
# package.  When installed via pip it will not be present, so we fall back
# to a lightweight app that covers the most common operations.
# ---------------------------------------------------------------------------

_SOURCE_CLI_DIR = Path(__file__).resolve().parent.parent / "cli"

_full_app_loaded = False

if _SOURCE_CLI_DIR.is_dir():
    sys.path.insert(0, str(_SOURCE_CLI_DIR))
    try:
        from zerodb_main import app  # noqa: F401

        _full_app_loaded = True
    except ImportError:
        pass

if not _full_app_loaded:
    # Minimal standalone app for pip-installed usage
    from zerodb_local import __version__

    app = typer.Typer(
        name="zerodb",
        help="ZeroDB Local CLI — manage your local ZeroDB environment",
        add_completion=False,
    )

    @app.command()
    def version():
        """Show zerodb-local version."""
        typer.echo(f"zerodb-local {__version__}")

    @app.command()
    def serve(
        host: str = typer.Option(
            "127.0.0.1",
            help="Bind address. 127.0.0.1 = this machine only; 0.0.0.0 = whole network "
            "(set ZERODB_LOCAL_API_KEY when you do)",
        ),
        port: int = typer.Option(8000, help="Port number"),
        reload: bool = typer.Option(False, help="Enable auto-reload"),
    ):
        """Start the ZeroDB Local API server."""
        import uvicorn

        typer.echo(f"Starting ZeroDB Local on {host}:{port}")
        import os

        if host not in ("127.0.0.1", "localhost", "::1") and not os.getenv("ZERODB_LOCAL_API_KEY", "").strip():
            typer.echo(
                f"Warning: listening on {host}: anyone who can reach this port can read and change "
                "your data. Set ZERODB_LOCAL_API_KEY to require a key, or use --host 127.0.0.1.",
                err=True,
            )
        uvicorn.run(
            "zerodb_local.server:create_app",
            factory=True,
            host=host,
            port=port,
            reload=reload,
        )

    @app.command()
    def health():
        """Check if the local ZeroDB server is running."""
        import httpx

        try:
            resp = httpx.get("http://localhost:8000/health", timeout=5)
            data = resp.json()
            typer.echo(f"Status: {data.get('status', 'unknown')}")
        except Exception as exc:
            typer.echo(f"Server unreachable: {exc}", err=True)
            raise typer.Exit(code=1)
