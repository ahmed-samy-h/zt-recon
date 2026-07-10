"""
ZT-RECON modules package.

Groups all the core building blocks of the tool:
    - scanner          -> Nmap host/port/service discovery + evasion
    - subdomain_enum   -> Passive subdomain discovery + liveness filtering
    - web_analyzer      -> HTTP headers/methods/source snippet analysis
    - exploit_suite     -> SQLMap / Dirsearch / Nuclei (OWASP Top 10 active scan)
    - ai_engine         -> Groq API integration for AI-driven vulnerability analysis
    - html_report       -> Converts the AI report into a styled HTML file
    - session_manager   -> Per-target scan state persistence (resumable scans)
    - auth              -> Groq API key storage/retrieval
    - banner            -> ASCII banner shown on startup
"""

__version__ = "1.0.0"