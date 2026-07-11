import os
import urllib.request
import pyfiglet
from contextlib import contextmanager
from rich.console import Console

console = Console()

TOOL_NAME = "ZT-RECON"
TAGLINE = "AI-Powered Automated Recon & Exploitation Orchestrator"
SUBTAGLINE = "Zero Trace • Red Team • Leave Nothing But Success"

# The target custom font and its remote source URL.
# NOTE: the file on xero/figlet-fonts is actually named "Big Money-ne.flf"
# -- capitalized, with a SPACE between "Big" and "Money-ne" -- not
# "big_money-ne.flf" (lowercase + underscore) like the old URL assumed.
# That mismatched filename is exactly why the old URL 404'd. The repo's
# default branch is also "main", not "master".
FONT_DISPLAY_NAME = "Big Money-ne"          # used for the on-disk file + pyfiglet font= lookup
FONT_FILENAME = "Big Money-ne.flf"
FONT_URL = "https://raw.githubusercontent.com/xero/figlet-fonts/main/Big%20Money-ne.flf"

# pyfiglet resolves font names by filename (minus .flf), so the candidate
# list needs to match FONT_DISPLAY_NAME exactly, spaces included.
FONT_CANDIDATES = [FONT_DISPLAY_NAME, "slant", "big", "standard"]

# Marker file: once a download attempt fails (404, DNS failure, no network,
# etc.), we drop a marker here so every FUTURE run skips the network call
# entirely instead of re-attempting (and re-failing) on every single launch.
# This is what was causing the "[-] Network Error ..." line to print on
# every run even though it never actually breaks anything -- it was just
# retrying a dead URL every time.
FONT_UNAVAILABLE_MARKER = "/tmp/.zt_recon_font_unavailable"


def ensure_font_installed():
    """Dynamically resolves the pyfiglet fonts directory and downloads the
    custom font if it is missing from the local environment. Skips the
    network call entirely if a previous attempt already failed (see
    FONT_UNAVAILABLE_MARKER above), so a broken/404 remote font source only
    ever costs one failed attempt total, not one per run.
    """
    if os.path.exists(FONT_UNAVAILABLE_MARKER):
        # Already tried and failed before -> go straight to fallback fonts,
        # no network call, no repeated error message.
        return

    try:
        # Resolving the absolute path of the pyfiglet package installation
        pyfiglet_base_dir = os.path.dirname(pyfiglet.__file__)
        fonts_directory = os.path.join(pyfiglet_base_dir, "fonts")
        target_font_path = os.path.join(fonts_directory, FONT_FILENAME)

        # Check if the font is already downloaded and present
        if not os.path.exists(target_font_path):
            console.print(f"[*] Custom font '{FONT_DISPLAY_NAME}' not found. Downloading via remote source...", style="yellow")

            # Downloading the raw .flf file directly into the pyfiglet fonts directory
            urllib.request.urlretrieve(FONT_URL, target_font_path)

            console.print(f"[+] Font '{FONT_DISPLAY_NAME}' successfully downloaded and integrated.", style="green")

    except PermissionError:
        # Handles global installation environments where writing requires sudo privileges
        console.print(
            f"[-] Permission Denied: Cannot write to pyfiglet directory. "
            f"Run as root/sudo or use a Python Virtual Environment (venv) to unlock custom fonts.",
            style="bold orange3"
        )
        _write_marker_safely()
    except Exception as e:
        # Handles network issues, DNS failures, or a moved/renamed remote
        # file (404) gracefully -> fall back to bundled fonts and remember
        # not to try again on the next run.
        console.print(f"[-] Network Error: Failed to fetch the custom font layout: {e}", style="red")
        console.print(f"[*] Falling back to bundled font. This won't be retried on future runs.", style="dim")
        _write_marker_safely()


def _write_marker_safely():
    """Best-effort marker write; if even /tmp isn't writable, we just accept
    that the download will be retried next run -- not worth crashing over."""
    try:
        with open(FONT_UNAVAILABLE_MARKER, "w") as f:
            f.write("font download previously failed, skipping retries")
    except OSError:
        pass


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