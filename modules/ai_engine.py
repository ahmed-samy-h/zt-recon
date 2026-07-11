import anthropic

# --------------------------------------------------------------------------
# Provider migration: Groq (llama-3.3-70b-versatile / gpt-oss-120b) has been
# fully removed from this project. The AI analysis engine now talks directly
# to Anthropic's Claude models.
#
#   - claude-sonnet-5           -> DEFAULT. Strong reasoning + good speed,
#                                  well suited for vuln/compliance mapping.
#   - claude-opus-4-8           -> deeper reasoning, slower, use via --model
#                                  for the toughest/most ambiguous targets.
#   - claude-haiku-4-5-20251001 -> fastest/cheapest, good for quick triage
#                                  passes or very large bulk scans.
# --------------------------------------------------------------------------
DEFAULT_MODEL = "claude-sonnet-5"

# Moved the "who/how to behave" instructions into a dedicated system prompt
# (instead of stuffing everything into the user message like the old Groq
# version did). This is standard best-practice prompt engineering for
# Claude: the system prompt sets persistent role/behavior, the user message
# carries only the actual data + task -> more consistent, better-grounded
# output turn after turn.
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
        self.client = anthropic.Anthropic(api_key=api_token)
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
        """Sends consolidated recon data to Claude for vulnerability analysis.
        Streams the response live to the console (as advertised) and also
        returns the full text so it can be turned into an HTML/PDF report."""
        prompt = self._build_prompt(scan_data, web_data, subdomain_data, owasp_data)
        full_text = ""

        try:
            with self.client.messages.stream(
                model=self.model,
                max_tokens=8192,
                temperature=0.2,  # low temperature -> more grounded, less "creative" output
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            ) as stream:
                for text_chunk in stream.text_stream:
                    full_text += text_chunk
                    if stream_to_console:
                        print(text_chunk, end="", flush=True)

            if stream_to_console:
                print()  # newline after streaming ends

            return full_text

        except Exception as e:
            error_msg = f"[-] Error interacting with AI Engine (Anthropic): {str(e)}"
            print(error_msg)
            return error_msg