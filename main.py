import sys
import os
import argparse
import hashlib
import time
from rich.console import Console

from modules.banner import display_banner
from modules.auth import initialize_auth
from modules.scanner import NetworkScanner
from modules.web_analyzer import analyze_web_target
from modules.ai_engine import AIEngine, DEFAULT_MODEL
from modules.subdomain_enum import is_domain, run_subdomain_recon
from modules.exploit_suite import run_owasp_suite
from modules.html_report import generate_html_report
import modules.session_manager as session

console = Console()


def get_session_dir(target):
    target_hash = hashlib.md5(target.encode("utf-8")).hexdigest()
    return os.path.join(session.SESSION_DIR, target_hash)


def main():
    display_banner()

    api_token = initialize_auth()
    if not api_token:
        console.print("[red][!] Valid Groq API Token is required to run this tool.[/red]")
        sys.exit(1)

    parser = argparse.ArgumentParser(description="ZT-RECON: AI-Powered Automated Recon & Exploitation Orchestrator")
    parser.add_argument("-t", "--target", help="Single Target IP or Domain")
    parser.add_argument("-f", "--file", help="File containing list of targets (Bulk Scan)")
    parser.add_argument("--delay", type=float, default=2.0, help="Throttling delay between scan phases (Rate Limiting)")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Groq model id to use for AI analysis")
    parser.add_argument("--no-subdomains", action="store_true", help="Skip subdomain enumeration")
    parser.add_argument("--no-owasp", action="store_true", help="Skip the active OWASP scan suite (SQLMap/Dirsearch/Nuclei)")
    parser.add_argument("--report-dir", default="./reports", help="Directory to save HTML reports")
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

    scanner = NetworkScanner(rate_limit_delay=args.delay)
    ai = AIEngine(api_token=api_token, model=args.model)

    for current_target in targets:
        console.print(f"\n[bold yellow][+] Processing Target: {current_target}[/bold yellow]")

        state = session.load_session(current_target) or {}
        session_dir = get_session_dir(current_target)


        if "open_ports" not in state or "infra_details" not in state:
            live_hosts = scanner.host_discovery(current_target)
            if not live_hosts:
                console.print("[red][-] No live hosts detected.[/red]")
                continue

            selected_host = live_hosts[0]
            console.print(f"[blue][*] Progressing with host: {selected_host}[/blue]")

            open_ports = scanner.scan_ports(selected_host)
            state["open_ports"] = open_ports
            state["selected_host"] = selected_host
            session.save_session(current_target, state)

            time.sleep(args.delay)

            infra_details = scanner.service_os_discovery(selected_host, open_ports)
            state["infra_details"] = infra_details
            session.save_session(current_target, state)
        else:
            console.print("[green][+] Resuming Infrastructure & Port Context from active session.[/green]")
            open_ports = state["open_ports"]
            infra_details = state["infra_details"]
            selected_host = state.get("selected_host", current_target)

        time.sleep(args.delay)


        subdomain_summary = None
        if not args.no_subdomains and is_domain(current_target):
            if "subdomain_summary" not in state:
                subdomain_summary = run_subdomain_recon(current_target, session_dir)
                state["subdomain_summary"] = subdomain_summary
                session.save_session(current_target, state)
            else:
                console.print("[green][+] Resuming Subdomain Context from active session.[/green]")
                subdomain_summary = state["subdomain_summary"]


        web_context = None
        owasp_data = None
        if 80 in open_ports or 443 in open_ports:
            protocol = "https" if 443 in open_ports else "http"
            web_url = state.get("web_url") or f"{protocol}://{selected_host}"
            state["web_url"] = web_url

            if "web_context" not in state:
                web_context = analyze_web_target(web_url)
                state["web_context"] = web_context
                session.save_session(current_target, state)
            else:
                console.print("[green][+] Resuming Web Context from active session.[/green]")
                web_context = state["web_context"]

            time.sleep(args.delay)

            if not args.no_owasp:
                if "owasp_data" not in state:
                    console.print("[bold magenta][*] Launching OWASP Top 10 active scan suite (SQLMap / Dirsearch / Nuclei)...[/bold magenta]")
                    owasp_data = run_owasp_suite(web_url, session_dir, delay=args.delay)
                    state["owasp_data"] = owasp_data
                    session.save_session(current_target, state)
                else:
                    console.print("[green][+] Resuming OWASP Scan Data from active session.[/green]")
                    owasp_data = state["owasp_data"]


        console.print("\n[bold cyan][*] Streaming AI Security Analysis...[/bold cyan]\n")
        report_text = ai.analyze_vulnerabilities(infra_details, web_context, subdomain_summary, owasp_data)
        generate_html_report(current_target, report_text, output_dir=args.report_dir, model_name=args.model)

        session.clear_session(current_target)


if __name__ == "__main__":
    main()
