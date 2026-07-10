from groq import Groq

# openai/gpt-oss-120b replaced the deprecated llama-3.3-70b-versatile on Groq
# (fast, strong reasoning, great for compliance/vuln mapping tasks).
# Swap to "moonshotai/kimi-k2-instruct-0905" if you want deeper reasoning
# quality at the cost of some speed.
DEFAULT_MODEL = "openai/gpt-oss-120b"


class AIEngine:
    def __init__(self, api_token, model=DEFAULT_MODEL):
        self.client = Groq(api_key=api_token)
        self.model = model

    def _build_prompt(self, scan_data, web_data=None, subdomain_data=None, owasp_data=None):
        return f"""
You are an expert cybersecurity auditor (Zero Trace methodology). Analyze the
following target data carefully and produce a professional security writeup.

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

Return the report in clean Markdown with clear headers (##) for each section above.
"""

    def analyze_vulnerabilities(self, scan_data, web_data=None, subdomain_data=None, owasp_data=None, stream_to_console=True):
        """Sends consolidated recon data to Groq for vulnerability analysis.
        Streams the response live to the console (as advertised) and also
        returns the full text so it can be turned into an HTML report."""
        prompt = self._build_prompt(scan_data, web_data, subdomain_data, owasp_data)
        full_text = ""

        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                stream=True,
                temperature=0.3,
            )

            for chunk in completion:
                delta = chunk.choices[0].delta.content or ""
                full_text += delta
                if stream_to_console:
                    print(delta, end="", flush=True)

            if stream_to_console:
                print()  # newline after streaming ends

            return full_text

        except Exception as e:
            error_msg = f"[-] Error interacting with AI Engine (Groq): {str(e)}"
            print(error_msg)
            return error_msg