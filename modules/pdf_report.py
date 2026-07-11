import os
from weasyprint import HTML


def generate_pdf_report(html_file_path, output_dir="./reports"):
    """Renders the already-generated 'Zero Trace' HTML report to a PDF file
    sitting right next to it, using WeasyPrint (a pure-Python HTML/CSS -> PDF
    engine). Since html_report.py already produces a single self-contained
    HTML file (inline <style>, no external assets), WeasyPrint can render it
    directly with no extra work — the PDF keeps the exact same black/red/
    silver theme as the HTML version."""
    os.makedirs(output_dir, exist_ok=True)

    pdf_path = os.path.splitext(html_file_path)[0] + ".pdf"
    HTML(filename=html_file_path).write_pdf(pdf_path)

    print(f"[+] PDF report saved -> {pdf_path}")
    return pdf_path