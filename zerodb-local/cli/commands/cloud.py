"""
Cloud Commands - Interact with ZeroDB Cloud

Story 3.3: Cloud Authentication Commands
Story 3.4: Project Linking Commands
"""
import typer
import requests
from rich.console import Console
from typing import Optional
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from ..config import (
        save_cloud_credentials,
        clear_cloud_credentials,
        get_cloud_credentials,
        set_project_id,
        load_config
    )
except ImportError:
    from config import (
        save_cloud_credentials,
        clear_cloud_credentials,
        get_cloud_credentials,
        set_project_id,
        load_config
    )

app = typer.Typer(help="Interact with ZeroDB Cloud")
console = Console()


@app.command("login")
def cloud_login(
    email: str = typer.Option(..., "--email", "-e", prompt=True, help="Email address"),
    password: str = typer.Option(..., "--password", "-p", prompt=True, hide_input=True, help="Password")
):
    """
    Login to ZeroDB Cloud

    Story 3.3: Reuses existing /auth/login endpoint
    """
    try:
        config = load_config()
        cloud_api_url = config.get('cloud_api_url', 'https://api.ainative.studio')

        console.print(f"[cyan]Logging in to {cloud_api_url}...[/cyan]")

        response = requests.post(
            f"{cloud_api_url}/auth/login",
            json={"email": email, "password": password},
            timeout=30
        )
        response.raise_for_status()

        tokens = response.json()
        save_cloud_credentials(tokens)

        user_email = tokens.get('user', {}).get('email', email)
        console.print(f"[green]✓[/green] Logged in as {user_email}")

    except requests.exceptions.RequestException as e:
        console.print(f"[red]Login failed:[/red] {str(e)}")
        raise typer.Exit(1)


@app.command("logout")
def cloud_logout():
    """Logout from ZeroDB Cloud"""
    clear_cloud_credentials()
    console.print("[green]✓[/green] Logged out successfully")


@app.command("whoami")
def cloud_whoami():
    """Show current logged-in user"""
    credentials = get_cloud_credentials()

    if not credentials:
        console.print("[yellow]Not logged in[/yellow]")
        console.print("Run 'zerodb cloud login' to authenticate")
        return

    user = credentials.get('user', {})
    console.print(f"[bold]Logged in as:[/bold] {user.get('email', 'Unknown')}")
    if user.get('name'):
        console.print(f"[bold]Name:[/bold] {user.get('name')}")
    if user.get('organization'):
        console.print(f"[bold]Organization:[/bold] {user.get('organization')}")


@app.command("link")
def cloud_link(
    project_id: str = typer.Argument(..., help="Cloud project ID to link")
):
    """
    Link local project to cloud project

    Story 3.4: Project Linking
    """
    try:
        credentials = get_cloud_credentials()
        if not credentials:
            console.print("[red]Error:[/red] Not logged in. Run 'zerodb cloud login' first.")
            raise typer.Exit(1)

        config = load_config()
        cloud_api_url = config.get('cloud_api_url', 'https://api.ainative.studio')

        # Verify project exists and user has access
        console.print(f"[cyan]Verifying project {project_id}...[/cyan]")

        response = requests.get(
            f"{cloud_api_url}/v1/projects/{project_id}",
            headers={'Authorization': f"Bearer {credentials.get('access_token')}"},
            timeout=30
        )
        response.raise_for_status()

        project = response.json()

        # Save link
        set_project_id(project_id)

        console.print(f"[green]✓[/green] Linked to cloud project: {project.get('name', project_id)}")
        console.print(f"  Project ID: {project_id}")

    except requests.exceptions.RequestException as e:
        console.print(f"[red]Link failed:[/red] {str(e)}")
        raise typer.Exit(1)


@app.command("unlink")
def cloud_unlink():
    """Unlink current project"""
    config = load_config()

    if not config.get('project_id'):
        console.print("[yellow]No project linked[/yellow]")
        return

    if typer.confirm("Unlink current project?"):
        set_project_id(None)
        console.print("[green]✓[/green] Project unlinked")


@app.command("create-from-local")
def cloud_create_from_local(
    name: str = typer.Option(..., "--name", "-n", prompt=True, help="Project name")
):
    """Create cloud project from local data"""
    console.print("[cyan]Creating cloud project from local data...[/cyan]")
    # TODO: Implement project creation and initial sync
    console.print("[yellow]Not yet implemented[/yellow]")


if __name__ == "__main__":
    app()
