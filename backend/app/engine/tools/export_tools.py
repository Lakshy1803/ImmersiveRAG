import csv
from io import StringIO
import re
import markdown
from xhtml2pdf import pisa
from io import BytesIO

def extract_tables_to_csv(markdown_text: str) -> str:
    """
    Extracts markdown tables from text and converts them to CSV format.
    If no tables are found, returns the raw text in a single CSV column.
    """
    # Find all table rows taking into account markdown table syntax
    lines = markdown_text.strip().split('\n')
    
    csv_buffer = StringIO()
    writer = csv.writer(csv_buffer)
    
    table_found = False
    in_table = False
    
    for line in lines:
        line = line.strip()
        if line.startswith('|') and line.endswith('|'):
            table_found = True
            in_table = True
            # Skip separator lines like |---|---|
            if re.match(r'^\|[-\s|:]+\|$', line):
                continue
            
            # Extract cells
            cells = [cell.strip() for cell in line.strip('|').split('|')]
            writer.writerow(cells)
        elif in_table:
            # End of table
            in_table = False
            writer.writerow([]) # Empty row between tables
            
    if not table_found:
        # If no table, just return the text as a single row
        writer.writerow(["Content"])
        writer.writerow([markdown_text])
        
    return csv_buffer.getvalue()

def generate_pdf_from_markdown(markdown_text: str) -> bytes:
    """
    Converts markdown text to HTML, then generates a PDF byte buffer using xhtml2pdf.
    """
    html_content = markdown.markdown(markdown_text, extensions=['tables', 'fenced_code'])
    
    # Add some basic styling for the PDF
    styled_html = f"""
    <html>
    <head>
    <style>
        body {{ font-family: Helvetica, Arial, sans-serif; font-size: 12pt; line-height: 1.5; color: #333; }}
        h1, h2, h3 {{ color: #1B1C1C; }}
        table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; font-weight: bold; }}
        pre {{ background-color: #f8f8f8; padding: 10px; border-radius: 5px; font-family: monospace; white-space: pre-wrap; }}
        code {{ font-family: monospace; background-color: #f8f8f8; padding: 2px 4px; border-radius: 3px; }}
        blockquote {{ border-left: 4px solid #eb8c00; margin-left: 0; padding-left: 15px; color: #555; font-style: italic; }}
    </style>
    </head>
    <body>
    {html_content}
    </body>
    </html>
    """
    
    pdf_buffer = BytesIO()
    pisa_status = pisa.CreatePDF(
        styled_html,
        dest=pdf_buffer
    )
    
    if pisa_status.err:
        raise Exception("Failed to generate PDF")
        
    return pdf_buffer.getvalue()
