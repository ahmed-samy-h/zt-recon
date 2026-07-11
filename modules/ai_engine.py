import socket
import time

from google import genai
from google.genai import types

# --------------------------------------------------------------------------
DEFAULT_MODEL = "gemini-3.5-flash"

# How many times to retry a failed API call when the failure LOOKS transient
# (DNS hiccup, connection reset, timeout) before giving up and returning the
# error string. Delays follow exponential backoff: 2s, 4s, 8s.
MAX_RETRIES = 3
RETRY_BACKOFF_BASE_SECONDS = 2


def _is_transient_network_error(exc):
    """Best-effort check for whether an exception looks like a temporary
    network/DNS hiccup (worth retrying) rather than a permanent failure like
    a bad/expired API key or an invalid model name (not worth retrying,
    since retrying those just wastes time and produces the same error).

    [Errno -3] Temporary failure in name resolution is the classic case:
    it is EAI_AGAIN under the hood, which glibc's resolver itself labels as
    transient (as opposed to EAI_NONAME/"not known" for a truly nonexistent
    host)."""
    if isinstance(exc, socket.gaierror):
        return True
    error_text = str(exc).lower()
    transient_markers = (
        "temporary failure in name resolution",
        "errno -3",
        "connection reset",
        "connection aborted",
        "timed out",
        "timeout",
        "eai_again",
        "network is unreachable",
    )
    return any(marker in error_text for marker in transient_markers)


SYSTEM_PROMPT = """You are an expert cybersecurity auditor operating under the
Zero Trace methodology. You analyze automated recon/exploitation-suite output
(Nmap, subdomain enumeration, HTTP analysis, SQLMap, Dirsearch, Nuclei) for a
single AUTHORIZED penetration-testing target and produce a precise, evidence
grounded security writeup.

Hard rules you must always follow:
- Never invent a finding, CVE, port, parameter, or header that does not
  appear in the data you were given.
- If a section has no supporting evidence, say so plainly instead of
  speculating or padding with generic filler.
- Prefer being specific and citing the exact data point (port number,
  parameter name, header, template id) over vague statements.
- Severity ratings must be justified by what is actually in the data."""


class AIEngine:
    def __init__(self, api_token, model=DEFAULT_MODEL):
        self.client = genai.Client(api_key=api_token)
        self.model = model

    def _build_prompt(self, scan_data, web_data=None, subdomain_data=None, owasp_data=None):
        return f"""Analyze the following target data carefully and produce a
professional security writeup.

## Network Scan Data
{scan_data}

## Web Architecture Data
{web_data if web_data else 'No active web entrypoint found.'}

## Subdomain Enumeration Data
{subdomain_data if subdomain_data else 'No subdomains were enumerated for this target.'}

## OWASP Top 10 Active Scan Data (SQLMap / Dirsearch / Nuclei)
{owasp_data if owasp_data else 'No active OWASP scan suite was run for this target.'}

## Tasks
1. 🚨 CRITICAL FINDINGS SUMMARY — a short, prioritized summary of the worst issues.
2. 🌐 WEB LAYER & HTTP ANALYSIS — headers, methods, forms, subdomains attack surface.
3. 🕳️ VULNERABILITY DETAILS — each finding, its severity, and the realistic attack path.
4. 🛠️ VERIFICATION COMMANDS — safe, ready-to-copy commands a tester can run manually
   to confirm each finding (assume the tester is authorized on this target).
5. 📋 COMPLIANCE MAPPING — map each finding to OWASP Top 10 and NIST CSF/CIS controls.
6. 🔒 DEFENSIVE REMEDIATION GUIDELINES — concrete steps to fix each issue.

Return the report in clean Markdown with clear headers (##) for each section
above. Ground every single claim strictly in the data provided above.
"""

    def analyze_vulnerabilities(self, scan_data, web_data=None, subdomain_data=None,
                                 owasp_data=None, stream_to_console=True):
        """Sends consolidated recon data to Gemini for vulnerability analysis.
        Streams the response live to the console (as advertised) and also
        returns the full text so it can be turned into an HTML/PDF report.

        Automatically retries (with exponential backoff) when the failure
        looks like a transient network/DNS hiccup rather than a permanent
        problem (bad key, invalid model, quota exhausted), since a single
        flaky DNS lookup shouldn't throw away an entire recon run's worth of
        scan data."""
        prompt = self._build_prompt(scan_data, web_data, subdomain_data, owasp_data)

        last_error = None
        for attempt in range(1, MAX_RETRIES + 1):
            full_text = ""
            try:
                stream = self.client.models.generate_content_stream(
                    model=self.model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_PROMPT,
                        temperature=0.2,  # low temperature -> more grounded, less "creative" output
                        max_output_tokens=8192,
                    ),
                )

                for chunk in stream:
                    text_chunk = chunk.text or ""
                    full_text += text_chunk
                    if stream_to_console:
                        print(text_chunk, end="", flush=True)

                if stream_to_console:
                    print()  # newline after streaming ends

                return full_text

            except Exception as e:
                last_error = e

                if not _is_transient_network_error(e) or attempt == MAX_RETRIES:
                    # Either a permanent-looking error (bad key, invalid
                    # model, quota, etc.) -> retrying won't help, fail now.
                    # Or we're out of retries -> fail now too.
                    break

                backoff_seconds = RETRY_BACKOFF_BASE_SECONDS * (2 ** (attempt - 1))
                print(
                    f"[!] AI Engine call failed (attempt {attempt}/{MAX_RETRIES}, "
                    f"looks transient: {e}). Retrying in {backoff_seconds}s..."
                )
                time.sleep(backoff_seconds)

        error_msg = f"[-] Error interacting with AI Engine (Google AI Studio): {str(last_error)}"
        print(error_msg)
        return error_msg