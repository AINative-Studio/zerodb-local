"""
Environment Commands - Manage environment settings

Story 3.8: Environment Switching Commands
"""
import typer
from rich.console import Console
from rich.table import Table
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from ..config import load_config, save_config
except ImportError:
    from config import load_config, save_config

app = typer.Typer(help="Manage environments")
console = Console()


ENVIRONMENTS = {
    'local': {
        'api_url': 'http://localhost:8000',
        'description': 'Local development environment'
    },
    'staging': {
        'api_url': 'https://staging-api.ainative.studio',
        'description': 'Staging environment'
    },
    'production': {
        'api_url': 'https://api.ainative.studio',
        'description': 'Production environment'
    }
}


@app.command("list")
def env_list():
    """List all configured environments"""
    config = load_config()
    active_env = config.get('active_env', 'local')

    table = Table(title="Environments")
    table.add_column("Environment", style="cyan")
    table.add_column("API URL", style="magenta")
    table.add_column("Status", style="green")
    table.add_column("Description")

    for env_name, env_config in ENVIRONMENTS.items():
        status = "✓ Active" if env_name == active_env else ""
        table.add_row(
            env_name,
            env_config['api_url'],
            status,
            env_config.get('description', '')
        )

    console.print(table)


@app.command("switch")
def env_switch(
    environment: str = typer.Argument(..., help="Environment to switch to")
):
    """Switch to a different environment"""
    if environment not in ENVIRONMENTS:
        console.print(f"[red]Error:[/red] Unknown environment: {environment}")
        console.print(f"Available: {', '.join(ENVIRONMENTS.keys())}")
        raise typer.Exit(1)

    config = load_config()
    config['active_env'] = environment
    config['cloud_api_url'] = ENVIRONMENTS[environment]['api_url']
    save_config(config)

    console.print(f"[green]✓[/green] Switched to environment: {environment}")
    console.print(f"  API URL: {ENVIRONMENTS[environment]['api_url']}")


@app.command("current")
def env_current():
    """Show current environment"""
    config = load_config()
    active_env = config.get('active_env', 'local')

    console.print(f"[bold]Current environment:[/bold] {active_env}")
    if active_env in ENVIRONMENTS:
        console.print(f"  API URL: {ENVIRONMENTS[active_env]['api_url']}")
        console.print(f"  Description: {ENVIRONMENTS[active_env].get('description', '')}")


if __name__ == "__main__":
    app()
