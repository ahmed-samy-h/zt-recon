"""
ZT-RECON modules package.

Groups all the core building blocks of the tool:
    - scanner          -> Nmap host/port/service discovery + evasion
    - subdomain_enum   -> Passive subdomain discovery + liveness filtering
    - web_analyzer      -> HTTP headers/methods/source snippet analysis
    - exploit_suite     -> SQLMap / Dirsearch / Nuclei (OWASP Top 10 active scan)
    - ai_engine         -> Google ai Studio integration for AI-driven vulnerability analysis
    - html_report       -> Converts the AI report into a styled HTML file
    - pdf_report        -> Renders the HTML report to a matching PDF file (WeasyPrint)
    - session_manager   -> Per-target scan state persistence (resumable scans)
    - auth              -> Google API key storage/retrieval
    - banner            -> ASCII banner + live phase-status spinner shown during scans
"""

__version__ = "2.0.0"