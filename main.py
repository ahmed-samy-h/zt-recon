import sys
import os
import argparse
import hashlib
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from rich.console import Console

from modules.banner import display_banner, phase_status
from modules.auth import initialize_auth
from modules.scanner import NetworkScanner
from modules.web_analyzer import analyze_web_target
from modules.ai_engine import AIEngine, DEFAULT_MODEL
from modules.subdomain_enum import is_domain, run_subdomain_recon
from modules.exploit_suite import run_owasp_suite
from modules.html_report import generate_html_report
from modules.pdf_report import generate_pdf_report
import modules.session_manager as session

console = Console()
# All console writes from worker threads go through this lock so that
# parallel bulk-scan output doesn't interleave into unreadable garbage.
console_lock = threading.Lock()

FULL_PORT_RANGE = "1-65535"


def get_session_dir(target):
    target_hash = hashlib.md5(target.encode("utf-8")).hexdigest()
    return os.path.join(session.SESSION_DIR, target_hash)


def resolve_port_range(args):
    """--full-scan is just a friendly shortcut for --ports 1-65535. If the
    user passes both, --ports (being the more explicit choice) wins."""
    if args.ports != "1-1024":
        return args.ports
    if args.full_scan:
        return FULL_PORT_RANGE
    return args.ports


def process_target(current_target, api_token, args):
    """Runs the full recon + exploitation + AI-analysis pipeline for a SINGLE
    target. Deliberately builds its own NetworkScanner and AIEngine instances
    on every call (instead of reusing one shared instance across targets),
    because python-nmap's PortScanner stores each scan's results as instance
    attributes -> sharing one instance across parallel threads (bulk mode
    with --threads > 1) would silently corrupt concurrent scans."""

    scanner = NetworkScanner(rate_limit_delay=args.delay)
    ai = AIEngine(api_token=api_token, model=args.model)
    port_range = resolve_port_range(args)

    # Live-streaming the AI's tokens straight to the console only makes sense
    # when a single target is being processed at a time. With --threads > 1,
    # several targets would try to print to the same console simultaneously
    # and the output would interleave into noise -> stream live only in the
    # sequential path, and just print a completion notice per target
    # otherwise (the full text still goes into the HTML/PDF report either way).
    stream_live = args.threads <= 1

    with console_lock:
        console.print(f"\n[bold yellow][+] Processing Target: {current_target}[/bold yellow]")

    state = session.load_session(current_target) or {}
    session_dir = get_session_dir(current_target)

    # If a cached session used a different port range than what was
    # requested this run, the cached open_ports/infra_details are no longer
    # trustworthy (e.g. resuming with --full-scan after an old 1-1024 run
    # would otherwise silently keep using the narrower port list) -> drop
    # the stale port-related state and re-scan with the newly requested range.
    if state.get("port_range") != port_range:
        state.pop("open_ports", None)
        state.pop("infra_details", None)
        state.pop("selected_host", None)

    if "open_ports" not in state or "infra_details" not in state:
        with phase_status(f"[*] Host discovery for {current_target}..."):
            live_hosts = scanner.host_discovery(current_target)

        if not live_hosts:
            with console_lock:
                console.print(f"[red][-] No live hosts detected for {current_target}.[/red]")
            return

        selected_host = live_hosts[0]
        with console_lock:
            console.print(f"[blue][*] Progressing with host: {selected_host}[/blue]")

        with phase_status(f"[*] Scanning ports on {selected_host} (range: {port_range})..."):
            open_ports = scanner.scan_ports(selected_host, port_range=port_range)
        state["open_ports"] = open_ports
        state["selected_host"] = selected_host
        state["port_range"] = port_range
        session.save_session(current_target, state)

        time.sleep(args.delay)

        with phase_status(f"[*] Service & OS fingerprinting on {selected_host}..."):
            infra_details = scanner.service_os_discovery(selected_host, open_ports)
        state["infra_details"] = infra_details
        session.save_session(current_target, state)
    else:
        with console_lock:
            console.print("[green][+] Resuming Infrastructure & Port Context from active session.[/green]")
        open_ports = state["open_ports"]
        infra_details = state["infra_details"]
        selected_host = state.get("selected_host", current_target)

    time.sleep(args.delay)

    subdomain_summary = None
    if not args.no_subdomains and is_domain(current_target):
        if "subdomain_summary" not in state:
            with phase_status(f"[*] Subdomain enumeration for {current_target}..."):
                subdomain_summary = run_subdomain_recon(current_target, session_dir)
            state["subdomain_summary"] = subdomain_summary
            session.save_session(current_target, state)
        else:
            with console_lock:
                console.print("[green][+] Resuming Subdomain Context from active session.[/green]")
            subdomain_summary = state["subdomain_summary"]

    web_context = None
    owasp_data = None
    if 80 in open_ports or 443 in open_ports:
        protocol = "https" if 443 in open_ports else "http"
        web_url = state.get("web_url") or f"{protocol}://{selected_host}"
        state["web_url"] = web_url

        if "web_context" not in state:
            with phase_status(f"[*] Web recon on {web_url}..."):
                web_context = analyze_web_target(web_url)
            state["web_context"] = web_context
            session.save_session(current_target, state)
        else:
            with console_lock:
                console.print("[green][+] Resuming Web Context from active session.[/green]")
            web_context = state["web_context"]

        time.sleep(args.delay)

        if not args.no_owasp:
            if "owasp_data" not in state:
                with console_lock:
                    console.print("[bold magenta][*] Launching OWASP Top 10 active scan suite (SQLMap / Dirsearch / Nuclei)...[/bold magenta]")
                with phase_status(f"[*] Running OWASP active-scan suite on {web_url}..."):
                    owasp_data = run_owasp_suite(web_url, session_dir, delay=args.delay)
                state["owasp_data"] = owasp_data
                session.save_session(current_target, state)
            else:
                with console_lock:
                    console.print("[green][+] Resuming OWASP Scan Data from active session.[/green]")
                owasp_data = state["owasp_data"]

    with console_lock:
        console.print(f"\n[bold cyan][*] Streaming AI Security Analysis for {current_target}...[/bold cyan]\n")

    report_text = ai.analyze_vulnerabilities(
        infra_details, web_context, subdomain_summary, owasp_data,
        stream_to_console=stream_live,
    )

    html_path = generate_html_report(current_target, report_text, output_dir=args.report_dir, model_name=args.model)

    if not args.no_pdf:
        try:
            generate_pdf_report(html_path, output_dir=args.report_dir)
        except Exception as e:
            with console_lock:
                console.print(f"[red][!] PDF export failed for {current_target}: {e}[/red]")

    with console_lock:
        console.print(f"[bold green][+] Finished target: {current_target}[/bold green]")

    session.clear_session(current_target)


def main():
    display_banner()

    api_token = initialize_auth()
    if not api_token:
        console.print("[red][!] Valid Anthropic API Key is required to run this tool.[/red]")
        sys.exit(1)

    parser = argparse.ArgumentParser(description="ZT-RECON: AI-Powered Automated Recon & Exploitation Orchestrator")
    parser.add_argument("-t", "--target", help="Single Target IP or Domain")
    parser.add_argument("-f", "--file", help="File containing list of targets (Bulk Scan)")
    parser.add_argument("--delay", type=float, default=2.0, help="Throttling delay between scan phases (Rate Limiting)")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Anthropic model id to use for AI analysis")
    parser.add_argument("--no-subdomains", action="store_true", help="Skip subdomain enumeration")
    parser.add_argument("--no-owasp", action="store_true", help="Skip the active OWASP scan suite (SQLMap/Dirsearch/Nuclei)")
    parser.add_argument("--no-pdf", action="store_true", help="Skip PDF export (HTML report is always generated)")
    parser.add_argument("--report-dir", default="./reports", help="Directory to save HTML/PDF reports")
    parser.add_argument("--ports", default="1-1024",
                         help="Port range/list to scan, in nmap -p syntax. Default: '1-1024' "
                              "(fast, well-known ports only). Examples: '1-65535' for a full TCP "
                              "sweep, or '1-1024,3306,8080,8443' for the fast range plus specific "
                              "extra ports.")
    parser.add_argument("--full-scan", action="store_true",
                         help="Shortcut for --ports 1-65535 (full TCP port sweep). Much slower than "
                              "the default 1-1024 range, but won't miss services commonly deployed "
                              "above port 1024 (MySQL 3306, Redis 6379, alt-HTTP 8080/8443, "
                              "Elasticsearch 9200, MongoDB 27017, RDP 3389, etc.). Ignored if "
                              "--ports is also explicitly set.")
    parser.add_argument("--threads", type=int, default=1,
                         help="Number of targets scanned in PARALLEL during bulk (-f) scans. "
                              "Has no effect with a single -t target.")
    args = parser.parse_args()

    if not args.target and not args.file:
        parser.print_help()
        sys.exit(1)

    targets = []
    if args.target:
        targets.append(args.target)
    if args.file:
        try:
            with open(args.file, "r") as f:
                targets.extend([line.strip() for line in f if line.strip()])
        except FileNotFoundError:
            console.print(f"[red][!] File not found: {args.file}[/red]")
            sys.exit(1)

    if args.threads > 1 and len(targets) > 1:
        console.print(
            f"[bold yellow][*] Bulk mode: scanning {len(targets)} targets "
            f"with {args.threads} parallel workers.[/bold yellow]"
        )
        with ThreadPoolExecutor(max_workers=args.threads) as executor:
            futures = {executor.submit(process_target, tgt, api_token, args): tgt for tgt in targets}
            for future in as_completed(futures):
                tgt = futures[future]
                try:
                    future.result()
                except Exception as e:
                    with console_lock:
                        console.print(f"[red][!] Target {tgt} failed: {e}[/red]")
    else:
        for current_target in targets:
            try:
                process_target(current_target, api_token, args)
            except Exception as e:
                console.print(f"[red][!] Target {current_target} failed: {e}[/red]")


if __name__ == "__main__":
    main()