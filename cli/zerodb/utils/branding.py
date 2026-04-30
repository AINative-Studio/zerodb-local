"""
ZeroDB Branding - ASCII Logo and Welcome Messages

Provides consistent branding across CLI and installers.
"""
from rich.console import Console

# ASCII ZERO logo
ZERO_LOGO = """
██████╗ ███████╗██████╗  ██████╗
╚════██╗██╔════╝██╔══██╗██╔═══██╗
 █████╔╝█████╗  ██████╔╝██║   ██║
██╔═══╝ ██╔══╝  ██╔══██╗██║   ██║
███████╗███████╗██║  ██║╚██████╔╝
╚══════╝╚══════╝╚═╝  ╚═╝ ╚═════╝
"""

TAGLINE = "ZeroDB - The AINative Database"


def print_logo(console: Console = None):
    """
    Print the ZeroDB logo with tagline

    Args:
        console: Rich Console instance (optional)
    """
    if console is None:
        console = Console()

    console.print(f"[bold cyan]{ZERO_LOGO}[/bold cyan]", highlight=False)
    console.print(f"[dim]{TAGLINE}[/dim]\n", style="cyan", justify="center")


def print_welcome_message(console: Console = None, duration: str = "60 seconds"):
    """
    Print welcome message for setup wizards

    Args:
        console: Rich Console instance (optional)
        duration: Expected setup duration
    """
    if console is None:
        console = Console()

    console.print(
        f"[bold]Welcome! Let's set up ZeroLocal in under {duration}.[/bold]\n",
        style="green"
    )


# Plain text version for bash scripts
BASH_LOGO = r'''
  ███████╗███████╗██████╗  ██████╗
  ╚══███╔╝██╔════╝██╔══██╗██╔═══██╗
    ███╔╝ █████╗  ██████╔╝██║   ██║
   ███╔╝  ██╔══╝  ██╔══██╗██║   ██║
  ███████╗███████╗██║  ██║╚██████╔╝
  ╚══════╝╚══════╝╚═╝  ╚═╝ ╚═════╝

  ZeroDB - The AINative Database
'''


def get_bash_logo() -> str:
    """
    Get logo formatted for bash scripts with color codes

    Returns:
        str: Colored logo for bash output
    """
    cyan = '\033[0;36m'
    bold = '\033[1m'
    dim = '\033[2m'
    nc = '\033[0m'

    return f"{bold}{cyan}{BASH_LOGO}{nc}\n"


def get_bash_welcome(duration: str = "60 seconds") -> str:
    """
    Get welcome message for bash scripts

    Args:
        duration: Expected setup duration

    Returns:
        str: Colored welcome message for bash
    """
    green = '\033[0;32m'
    bold = '\033[1m'
    nc = '\033[0m'

    return f"{bold}{green}Welcome! Let's set up ZeroLocal in under {duration}.{nc}\n"
