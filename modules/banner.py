import pyfiglet
from rich.console import Console

console = Console()

TOOL_NAME = "ZT-RECON"
TAGLINE = "AI-Powered Automated Recon & Exploitation Orchestrator"
SUBTAGLINE = "Zero Trace • Zero Noise • Full Coverage"


def display_banner():
    ascii_art = pyfiglet.figlet_format(TOOL_NAME, font="ansi_shadow")
    console.print(f"[bold green]{ascii_art}[/bold green]")
    console.print(f"[bold blue]        {TAGLINE}[/bold blue]")
    console.print(f"[dim]                  {SUBTAGLINE}[/dim]\n")