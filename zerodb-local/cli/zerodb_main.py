#!/usr/bin/env python3
"""
ZeroDB CLI - Main entry point with new init wizard commands

Manages local ZeroDB environment with interactive setup wizard.

Refs #1132
"""
import sys
from pathlib import Path

# Add CLI directory to path
sys.path.insert(0, str(Path(__file__).parent))

import typer
from rich.console import Console

# Import new commands
from zerodb.commands.init import app as init_app
from zerodb.commands.status import app as status_app
from zerodb.commands.logs import app as logs_app
from zerodb.commands.dashboard import app as dashboard_app

# Import existing commands
from commands import sync, local, cloud, env, inspect, schema, serve

# Import branding
from zerodb.utils.branding import print_logo

# Create main app
app = typer.Typer(
    name="zerodb",
    help="ZeroDB Local CLI - Manage local ZeroDB environment and sync with cloud",
    add_completion=False
)
console = Console()

# Register new top-level commands
app.add_typer(init_app, name="init", help="Initialize ZeroDB environment with setup wizard")
app.add_typer(status_app, name="status", help="Check service status and health")
app.add_typer(logs_app, name="logs", help="View service logs")
app.add_typer(dashboard_app, name="dashboard", help="Open web dashboard")

# Register existing command groups
app.add_typer(sync.app, name="sync", help="Sync between local and cloud")
app.add_typer(local.app, name="local", help="Manage local ZeroDB environment")
app.add_typer(cloud.app, name="cloud", help="Interact with ZeroDB Cloud")
app.add_typer(env.app, name="env", help="Manage environments")
app.add_typer(inspect.app, name="inspect", help="Inspect local database state")
app.add_typer(schema.app, name="schema", help="Generate Pydantic models from table schemas")
app.add_typer(serve.app, name="serve", help="Start local ZeroDB server")


@app.command()
def version():
    """Show CLI version"""
    print_logo(console)
    console.print("[bold]Version:[/bold] v1.0.0\n")
    console.print("[bold]Features:[/bold]")
    console.print("  • [green]zerodb init[/green] - Interactive setup wizard")
    console.print("  • [green]zerodb status[/green] - Service health checks")
    console.print("  • [green]zerodb logs[/green] - View service logs")
    console.print("  • [green]zerodb dashboard[/green] - Open web dashboard")
    console.print("  • [green]zerodb sync[/green] - Sync with cloud")
    console.print("  • [green]zerodb cloud[/green] - Cloud authentication")
    console.print("  • [green]zerodb schema[/green] - Generate Pydantic models from tables")
    console.print("  • [green]zerodb serve[/green] - Start local server")


if __name__ == "__main__":
    app()
