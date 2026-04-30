"""
ZeroDB dashboard command - Open web dashboards

Open ZeroDB dashboard or service-specific dashboards in browser.

Refs #1132
"""
import typer
import webbrowser
import subprocess
from pathlib import Path
from typing import Optional
from rich.console import Console

app = typer.Typer(help="Open ZeroDB dashboard")
console = Console()

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.resolve()
DOCKER_COMPOSE_FILE = PROJECT_ROOT / "docker-compose.yml"

# Service dashboard URLs
DASHBOARD_URLS = {
    'main': 'http://localhost:3000',
    'dashboard': 'http://localhost:3000',
    'minio': 'http://localhost:9001',
    'qdrant': 'http://localhost:6333/dashboard',
    'api': 'http://localhost:8000/docs'
}


def check_service_running(service_name: str) -> bool:
    """
    Check if a service is running

    Args:
        service_name: Name of the service

    Returns:
        bool: True if running
    """
    try:
        result = subprocess.run(
            ["docker-compose", "-f", str(DOCKER_COMPOSE_FILE), "ps", "-q", service_name],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=str(PROJECT_ROOT)
        )
        return bool(result.stdout.strip())
    except:
        return False


@app.command()
def dashboard(
    service: Optional[str] = typer.Argument(None, help="Service dashboard to open (main, minio, qdrant, api)"),
    port: Optional[int] = typer.Option(None, "--port", "-p", help="Custom port"),
    no_browser: bool = typer.Option(False, "--no-browser", help="Don't open browser, just show URL")
):
    """
    Open ZeroDB dashboard in browser

    Examples:
        zerodb dashboard              # Open main dashboard
        zerodb dashboard minio        # Open MinIO console
        zerodb dashboard qdrant       # Open Qdrant dashboard
        zerodb dashboard api          # Open API docs
    """
    # Determine which dashboard to open
    if not service or service == 'main':
        service = 'dashboard'

    # Get URL
    url = DASHBOARD_URLS.get(service)
    if not url:
        console.print(f"[red]Unknown service: {service}[/red]")
        console.print("\nAvailable services:")
        for svc in DASHBOARD_URLS.keys():
            if svc != 'main':
                console.print(f"  • {svc}")
        raise typer.Exit(1)

    # Override port if specified
    if port:
        url = url.split(':')
        url = f"{url[0]}:{url[1]}:{port}"

    # Check if service is running
    if service == 'dashboard':
        check_name = 'dashboard'
    elif service == 'api':
        check_name = 'zerodb-api'
    else:
        check_name = service

    if not check_service_running(check_name):
        console.print(f"[red]Error:[/red] {service} is not running")
        console.print("\nStart services with: [cyan]zerodb init[/cyan] or [cyan]zerodb local up[/cyan]")
        raise typer.Exit(1)

    # Show URL
    console.print(f"\n[cyan]Dashboard URL:[/cyan] {url}\n")

    # Open in browser
    if not no_browser:
        try:
            webbrowser.open(url)
            console.print("[green]✓[/green] Opened in default browser")
        except Exception as e:
            console.print(f"[yellow]Could not open browser: {e}[/yellow]")
            console.print(f"Please open manually: {url}")
    else:
        console.print("Use [cyan]--no-browser[/cyan] flag removed to open in browser")


if __name__ == "__main__":
    app()
