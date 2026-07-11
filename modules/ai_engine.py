from google import genai
from google.genai import types

# --------------------------------------------------------------------------
# Provider migration: Anthropic Claude has been replaced with Google AI
# Studio (the Gemini Developer API), mainly to take advantage of its
# free tier (no credit card required) and its much larger context window,
# which comfortably fits the large combined Nmap + subdomain + web +
# SQLMap/Dirsearch/Nuclei prompt this tool sends for a single target.
#
#   - gemini-flash-latest -> DEFAULT. Free-tier eligible, huge context
#                            window, good speed/quality tradeoff for
#                            vuln/compliance mapping.
#   - gemini-pro-latest   -> deeper reasoning, no free tier, use via
#                            --model for the toughest/most ambiguous
#                            targets.
#   - gemini-flash-lite-latest -> fastest/cheapest/highest free-tier rate
#                            limit, good for quick triage passes or very
#                            large bulk scans.
#
# NOTE: Google's free-tier request/token limits change over time and are
# tracked per Google Cloud *project*, not per API key -> check the live
# quota for your own project at aistudio.google.com before relying on a
# specific number.
# --------------------------------------------------------------------------
DEFAULT_MODEL = "gemini-flash-latest"

# Moved the "who/how to behave" instructions into a dedicated system
# instruction (instead of stuffing everything into the user message). This
# is standard best-practice prompt engineering for Gemini: the system
# instruction sets persistent role/behavior, the user message carries only
# the actual data + task -> more consistent, better-grounded output turn
# after turn.
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
        returns the full text so it can be turned into an HTML/PDF report."""
        prompt = self._build_prompt(scan_data, web_data, subdomain_data, owasp_data)
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
            error_msg = f"[-] Error interacting with AI Engine (Google AI Studio): {str(e)}"
            print(error_msg)
            return error_msg