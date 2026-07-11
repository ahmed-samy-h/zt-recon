import os
import urllib.request
import pyfiglet
from contextlib import contextmanager
from rich.console import Console

console = Console()

TOOL_NAME = "ZT-RECON"
TAGLINE = "AI-Powered Automated Recon & Exploitation Orchestrator"
SUBTAGLINE = "Zero Trace • Red Team • Leave Nothing But Success"

# The target custom font and its remote source URL
FONT_NAME = "big_money-ne"
FONT_FILENAME = f"{FONT_NAME}.flf"
FONT_URL = f"https://raw.githubusercontent.com/xero/figlet-fonts/master/{FONT_FILENAME}"

# Fallback matrix in case the download fails or lacks permissions
FONT_CANDIDATES = [FONT_NAME, "slant", "big", "standard"]


def ensure_font_installed():
    """Dynamically resolves the pyfiglet fonts directory and downloads the

    custom font if it is missing from the local environment.
    """
    try:
        # Resolving the absolute path of the pyfiglet package installation
        pyfiglet_base_dir = os.path.dirname(pyfiglet.__file__)
        fonts_directory = os.path.join(pyfiglet_base_dir, "fonts")
        target_font_path = os.path.join(fonts_directory, FONT_FILENAME)

        # Check if the font is already downloaded and present
        if not os.path.exists(target_font_path):
            console.print(f"[*] Custom font '{FONT_NAME}' not found. Downloading via remote source...", style="yellow")
            
            # Downloading the raw .flf file directly into the pyfiglet fonts directory
            urllib.request.urlretrieve(FONT_URL, target_font_path)
            
            console.print(f"[+] Font '{FONT_NAME}' successfully downloaded and integrated.", style="green")
            
    except PermissionError:
        # Handles global installation environments where writing requires sudo privileges
        console.print(
            f"[-] Permission Denied: Cannot write to pyfiglet directory. "
            f"Run as root/sudo or use a Python Virtual Environment (venv) to unlock custom fonts.", 
            style="bold orange3"
        )
    except Exception as e:
        # Handles network issues or offline environments gracefully
        console.print(f"[-] Network Error: Failed to fetch the custom font layout: {e}", style="red")


def _render_ascii(text):
    for font in FONT_CANDIDATES:
        try:
            return pyfiglet.figlet_format(text, font=font)
        except (pyfiglet.FontNotFound, Exception):
            continue
    return f"\n{text}\n"


def display_banner():
    # Ensure the dynamic installation routine runs before rendering the banner
    ensure_font_installed()
    
    ascii_art = _render_ascii(TOOL_NAME)
    
    # Safe printing using direct style mapping to prevent brackets parsing bugs
    console.print(ascii_art, style="bold red")
    console.print(f"        [bold white]{TAGLINE}[/bold white]")
    console.print(f"                  [dim]{SUBTAGLINE}[/dim]\n")


@contextmanager
def phase_status(message: str, spinner_style: str = "dots"):
    """Shows a LIVE animated spinner + message while a scan phase is running."""
    with console.status(f"[bold red]{message}[/bold red]", spinner=spinner_style) as status:
        yield status


if __name__ == "__main__":
    display_banner()
    
    # Quick visual confirmation test
    import time
    with phase_status("[*] Initializing Zero Trace AI core components..."):
        time.sleep(2)
    console.print("[+] System core initialized successfully.", style="green")