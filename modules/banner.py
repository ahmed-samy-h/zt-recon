import pyfiglet
from contextlib import contextmanager
from rich.console import Console

console = Console()

TOOL_NAME = "ZT-RECON"
TAGLINE = "AI-Powered Automated Recon & Exploitation Orchestrator"
SUBTAGLINE = "Zero Trace • Red Team • Leave Nothing But Success"

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
    console.print(f"[bold red]{ascii_art}[/bold red]")
    console.print(f"[bold white]        {TAGLINE}[/bold white]")
    console.print(f"[dim]                  {SUBTAGLINE}[/dim]\n")


@contextmanager
def phase_status(message: str, spinner_style: str = "dots"):
    """Shows a LIVE animated spinner + message while a scan phase is running,
    so the operator has continuous visual confirmation that the tool is
    actively working (instead of the terminal looking frozen during long
    nmap / sqlmap / dirsearch / nuclei calls, which can silently take
    minutes with zero stdout in between).

    Usage:
        with phase_status("[*] Scanning ports on 10.10.10.5..."):
            open_ports = scanner.scan_ports(ip)

    The spinner automatically disappears and the console returns to normal
    print/console.print behaviour the moment the `with` block exits (success
    OR exception), so it is always safe to wrap any blocking call with it.
    """
    with console.status(f"[bold red]{message}[/bold red]", spinner=spinner_style) as status:
        yield status