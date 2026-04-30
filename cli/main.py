#!/usr/bin/env python3
"""
ZeroDB Local CLI - Main entry point

Manages local ZeroDB environment, cloud sync, and project operations.
"""
import sys
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

import typer
from typing import Optional
from rich.console import Console

from commands import sync, local, cloud, env, inspect

app = typer.Typer(
    name="zerodb",
    help="ZeroDB Local CLI - Manage local ZeroDB environment and sync with cloud",
    add_completion=False
)
console = Console()

# Register command groups
app.add_typer(sync.app, name="sync", help="Sync between local and cloud")
app.add_typer(local.app, name="local", help="Manage local ZeroDB environment")
app.add_typer(cloud.app, name="cloud", help="Interact with ZeroDB Cloud")
app.add_typer(env.app, name="env", help="Manage environments")
app.add_typer(inspect.app, name="inspect", help="Inspect local database state")


@app.command()
def version():
    """Show CLI version"""
    console.print("[bold cyan]ZeroDB Local CLI[/bold cyan] v1.0.0")


if __name__ == "__main__":
    app()
