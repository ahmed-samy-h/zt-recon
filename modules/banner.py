import pyfiglet
from rich.console import Console

console = Console()

TOOL_NAME = "ZT-RECON"
TAGLINE = "AI-Powered Automated Recon & Exploitation Orchestrator"
SUBTAGLINE = "Zero Trace • Zero Noise • Full Coverage"

# Preferred font first, then safe fallbacks that ship with almost every
# pyfiglet install (including minimal Debian/apt packages).
FONT_CANDIDATES = ["ansi_shadow", "slant", "big", "standard"]


def _render_ascii(text):
    for font in FONT_CANDIDATES:
        try:
            return pyfiglet.figlet_format(text, font=font)
        except pyfiglet.FontNotFound:
            continue
    # Absolute last resort: no figlet font available at all, just print plain text
    return f"\n{text}\n"


def display_banner():
    ascii_art = _render_ascii(TOOL_NAME)
    console.print(f"[bold green]{ascii_art}[/bold green]")
    console.print(f"[bold blue]        {TAGLINE}[/bold blue]")
    console.print(f"[dim]                  {SUBTAGLINE}[/dim]\n")