# ZT-RECON

AI-Powered Automated Recon & Exploitation Orchestrator.

Combines Nmap (with firewall/WAF evasion), passive subdomain enumeration +
liveness filtering, an OWASP Top 10 active scan suite (SQLMap / Dirsearch /
Nuclei), and AI-driven vulnerability analysis (via **Google AI Studio /
Gemini**) into a single command — with a live-streamed terminal report
(animated "working" spinner during long scans), a styled **"Zero Trace //
Red Team"** HTML report, and an auto-generated **PDF** twin of that same
report.

> ⚠️ For use only against targets you own or are explicitly authorized to test.

## What's new in v2.1.0

- 🤖 **AI engine switched to Google AI Studio (Gemini)** (was Anthropic
  Claude). Default model: `gemini-3.5-flash` — free tier eligible, no
  credit card required. Use `--model gemini-pro-latest` for deeper
  reasoning (paid tier only), or `--model gemini-flash-lite-latest` for
  fast/cheap triage with the highest free-tier rate limit.
- 🎨 **New terminal banner font** (`Big Money-ne`), still rendered in the
  same red "Zero Trace" style.
- 🔁 **Automatic retry on transient AI failures**: before giving up, the AI
  engine now detects failures that *look* transient (DNS hiccup, connection
  reset/aborted, timeout) and retries automatically up to 3 times with
  exponential backoff (2s, 4s, 8s). Failures that look permanent (bad/expired
  key, invalid model name, quota exhausted) are **not** retried — they fail
  immediately instead of wasting time reproducing the same error.
- 🧯 **Clearer AI-failure reporting**: if the AI call still fails after
  retries (quota exhausted, bad key, rate limit, etc.), the HTML/PDF report
  now shows an explicit "⚠️ AI Analysis Unavailable" section with the raw
  error instead of silently embedding the error text as if it were a real
  finding. The raw scan data is still saved either way, and re-running the
  same target resumes from cache and only retries the AI step.
- 📄 **`--report-format` replaces `--no-pdf`**: instead of always generating
  the HTML report and optionally skipping the PDF, you now explicitly choose
  which file(s) to keep with `--report-format {html,pdf,both}` (default
  `both`). Picking `pdf` treats the HTML file as a throwaway intermediate
  (WeasyPrint renders the PDF from it, then the HTML file is deleted).
  Picking `html` or `pdf` (i.e. anything other than the default `both`)
  also turns off live-streaming the AI report text to the terminal — it's
  written straight to the report file(s) only. With the default `both`,
  live streaming still happens exactly as before (single-target /
  `--threads 1` runs).

## What's new in v2.0.0

- 🎨 **New "Zero Trace // Red Team" HTML theme** (black / red / silver),
  matching the project's brand mark.
- 📄 **PDF export** of every report, automatically generated next to the
  HTML file (disable with `--no-pdf`). *(Superseded in v2.1.0 — see
  `--report-format` above; `--no-pdf` no longer exists.)*
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

> ⚠️ **One-time exception on your first update to v2.1.0:** the AI provider
> changed from Anthropic to Google AI Studio, and the key file itself was
> renamed (`.google_api_key`). This means the tool
> will ask you for a **new Google AI Studio API key**, free at
> aistudio.google.com, the first time you run it after updating — this is
> expected, not a bug. Your old Anthropic key file is simply left untouched
> on disk and unused.
>
> ℹ️ **Note on key formats (`AIzaSy...` vs `AQ....`):** Google has been
> rolling out a new `AQ.`-prefixed key format alongside the older
> `AIzaSy...` format. Both work fine with this tool, since it talks to
> Gemini natively through the `google-genai` SDK — the reports of `AQ.`
> keys failing are specific to OpenAI-compatible wrapper layers or
> third-party tools that hardcode a regex expecting the old `AIzaSy`
> prefix, which ZT-RECON does not do. `auth.py` no longer warns about
> `AQ.` keys (an earlier version incorrectly flagged them as broken).

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
sudo zt-recon -t example.com --no-subdomains --no-owasp --report-format html

# Use a different Gemini model
sudo zt-recon -t example.com --model gemini-pro-latest

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
- **`--model`** (default `gemini-3.5-flash`) — Google AI Studio (Gemini)
  model for the AI analysis. Also accepts `gemini-pro-latest` (deeper
  reasoning, paid tier only) or `gemini-flash-lite-latest`
  (fastest/cheapest, highest free-tier request rate — good for bulk triage).
- **`--no-subdomains`** — Skip the subdomain enumeration phase entirely.
- **`--no-owasp`** — Skip the active OWASP scan suite (SQLMap / Dirsearch /
  Nuclei) — recon only, no active exploitation attempts.
- **`--report-format`** (default `both`) — Which report file(s) to keep in
  `--report-dir`: `html` (HTML only), `pdf` (PDF only, the intermediate
  HTML file is deleted after the PDF is rendered from it), or `both`
  (default, keeps both files). Picking `html` or `pdf` explicitly also
  turns off live-streaming the AI report text to the terminal (it's written
  straight to the report file(s) instead); the default `both` still streams
  live exactly as before, as long as `--threads` is `1`.
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

First run will prompt for a Google AI Studio API key (get one free at
aistudio.google.com — no credit card required), stored at
`/opt/zt-recon/.google_api_key`.

> ℹ️ **About the free tier:** `gemini-3.5-flash` (the default model) is free-tier eligible
> with a generous context window (large enough for most combined
> Nmap/subdomain/web/OWASP prompts), but Google's exact free-tier
> request/token limits change over time and are tracked per Google Cloud
> *project*, not per API key. If you hit a `429`/quota error on a very
> large bulk scan, check your live limits at aistudio.google.com, or use
> `--threads 1` and a bit more `--delay` to slow down request pacing.

See `ZT-RECON_WRITEUP.md` for full architecture details.