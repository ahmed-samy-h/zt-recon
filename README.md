# ZT-RECON

AI-Powered Automated Recon & Exploitation Orchestrator.

Combines Nmap (with firewall/WAF evasion), passive subdomain enumeration +
liveness filtering, an OWASP Top 10 active scan suite (SQLMap / Dirsearch /
Nuclei), and AI-driven vulnerability analysis (via **Anthropic Claude**) into
a single command — with a live-streamed terminal report (animated "working"
spinner during long scans), a styled **"Zero Trace // Red Team"** HTML
report, and an auto-generated **PDF** twin of that same report.

> ⚠️ For use only against targets you own or are explicitly authorized to test.

## What's new in v2.0.0

- 🤖 **AI engine switched to Anthropic Claude** (was Groq). Default model:
  `claude-sonnet-5`. Use `--model claude-opus-4-8` for deeper reasoning, or
  `--model claude-haiku-4-5-20251001` for fast/cheap triage on large bulk scans.
- 🎨 **New "Zero Trace // Red Team" HTML theme** (black / red / silver),
  matching the project's brand mark.
- 📄 **PDF export** of every report, automatically generated next to the
  HTML file (disable with `--no-pdf`).
- 🧵 **Parallel bulk scanning**: `--threads N` scans multiple targets from a
  `-f targets.txt` file at the same time (defaults to `1` = sequential,
  same behavior as before).
- 🔍 **Deeper SQLMap parsing**: findings are now parsed directly from
  SQLMap's own on-disk session `log` files (parameter, type, title, payload)
  instead of relying only on stdout text-matching.
- ⏳ **Live "working" spinner** during every long-running phase (host
  discovery, port scan, OS fingerprinting, subdomain enum, web recon, OWASP
  suite), so the terminal never looks frozen.
- 🎯 **Configurable port range**: the port scan used to be hardcoded to
  `1-1024`, silently missing services on higher ports (MySQL `3306`, Redis
  `6379`, alt-HTTP `8080`/`8443`, Elasticsearch `9200`, MongoDB `27017`,
  etc.). Now you can control it with `--ports` (custom nmap-style range or
  list) or the `--full-scan` shortcut for a full `1-65535` sweep.

See `ZT-RECON_WRITEUP.md` for the full architecture breakdown of every layer.

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

## Updating an existing installation

If you already cloned and installed ZT-RECON before, update it like this
from inside your existing clone folder:

```bash
git pull origin main
chmod +x install.sh
sudo ./install.sh
```

`install.sh` re-copies the project into `/opt/zt-recon` and re-installs any
new/changed Python dependencies from `requirements.txt`, so re-running it is
always safe and idempotent.

> ⚠️ **One-time exception on your first update to v2.0.0:** the AI provider
> changed from Groq to Anthropic, and the key file itself was renamed
> (`.groq_api_key` → `.anthropic_api_key`). This means the tool will ask you
> for a **new Anthropic API key** (`sk-ant-...`, from console.anthropic.com)
> the first time you run it after updating — this is expected, not a bug.
> Your old Groq key file is simply left untouched on disk and unused.

A convenience `update.sh` script (does the same two steps above) is also
included in the repo — just run:

```bash
sudo ./update.sh
```

## Usage

```bash
# Single target — full pipeline
sudo zt-recon -t example.com

# Bulk targets from a file, sequential (safe default)
sudo zt-recon -f targets.txt

# Bulk targets, 5 targets scanned in PARALLEL
sudo zt-recon -f targets.txt --threads 5

# Stealth mode with delay between phases
sudo zt-recon -t example.com --delay 2.5

# Skip subdomain enum, the active OWASP suite, and/or PDF export
sudo zt-recon -t example.com --no-subdomains --no-owasp --no-pdf

# Use a different Claude model
sudo zt-recon -t example.com --model claude-opus-4-8

# Full 1-65535 TCP port sweep instead of the default fast 1-1024 range
sudo zt-recon -t example.com --full-scan

# Custom port range/list (nmap -p syntax)
sudo zt-recon -t example.com --ports "1-1024,3306,5432,6379,8080,8443,9200,27017"

# Custom report output directory
sudo zt-recon -t example.com --report-dir /home/user/client_x_reports
```

### All flags

- **`-t`, `--target`** — Single target IP or domain.
- **`-f`, `--file`** — Path to a text file with one target per line (bulk scan).
- **`--delay`** (default `2.0`) — Seconds to wait between scan phases (Nmap
  phases, subdomain probing, OWASP tools) — rate limiting to look less like
  a bot.
- **`--model`** (default `claude-sonnet-5`) — Anthropic model for the AI
  analysis. Also accepts `claude-opus-4-8` (deeper reasoning) or
  `claude-haiku-4-5-20251001` (fastest/cheapest, good for bulk triage).
- **`--no-subdomains`** — Skip the subdomain enumeration phase entirely.
- **`--no-owasp`** — Skip the active OWASP scan suite (SQLMap / Dirsearch /
  Nuclei) — recon only, no active exploitation attempts.
- **`--no-pdf`** — Skip PDF export; the HTML report is still always
  generated.
- **`--report-dir`** (default `./reports`) — Directory where HTML/PDF
  reports are saved.
- **`--ports`** (default `1-1024`) — Port range/list to scan, in nmap `-p`
  syntax (e.g. `1-65535`, `22,80,443`, or `1-1024,3306,8080`).
- **`--full-scan`** — Shortcut for `--ports 1-65535` (full TCP sweep).
  Ignored if `--ports` is also explicitly set.
- **`--threads`** (default `1`) — Number of targets scanned in parallel
  during bulk (`-f`) scans. No effect with a single `-t` target.

> ⚠️ **Note on `--ports` / `--full-scan`:** the default `1-1024` range only
> covers the "well-known" ports and can silently miss services on higher
> ports (MySQL `3306`, PostgreSQL `5432`, Redis `6379`, alt-HTTP
> `8080`/`8443`, Elasticsearch `9200`, MongoDB `27017`, RDP `3389`, etc.).
> Use `--full-scan` or a custom `--ports` list whenever full port coverage
> matters more than scan speed. If you resume a scan with a different port
> range than the one used previously for the same target, ZT-RECON detects
> the mismatch and automatically re-scans ports instead of reusing stale
> cached results.

First run will prompt for an Anthropic API key (get one at
console.anthropic.com), stored at `/opt/zt-recon/.anthropic_api_key`.

See `ZT-RECON_WRITEUP.md` for full architecture details.