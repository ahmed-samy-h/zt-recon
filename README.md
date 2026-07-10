# ZT-RECON

AI-Powered Automated Recon & Exploitation Orchestrator.

Combines Nmap (with firewall/WAF evasion), passive subdomain enumeration +
liveness filtering, an OWASP Top 10 active scan suite (SQLMap / Dirsearch /
Nuclei), and AI-driven vulnerability analysis (via Groq) into a single
command — with a live-streamed terminal report and a styled HTML report.

> ⚠️ For use only against targets you own or are explicitly authorized to test.

## Clone

```bash
git clone https://github.com/ahmed-samy-h/zt-recon.git
cd ZT-Recon
```

## Install

```bash
chmod +x install.sh
sudo ./install.sh
```

## Usage

```bash
# Single target — full pipeline
sudo zt-recon -t example.com

# Bulk targets from a file
sudo zt-recon -f targets.txt

# Stealth mode with delay between phases
sudo zt-recon -t example.com --delay 2.5

# Skip subdomain enum and/or the active OWASP suite
sudo zt-recon -t example.com --no-subdomains --no-owasp

# Use a different Groq model
sudo zt-recon -t example.com --model moonshotai/kimi-k2-instruct-0905
```

First run will prompt for a Groq API key (get one free at console.groq.com),
stored at `/opt/zt-recon/.groq_api_key`.

See `ZT-RECON_WRITEUP.md` for full architecture details.
