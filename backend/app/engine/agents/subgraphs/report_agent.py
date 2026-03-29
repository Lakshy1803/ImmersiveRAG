import logging
import os
import markdown
from xhtml2pdf import pisa
from langgraph.graph import StateGraph, END
from app.engine.agents.state import AgentState

from pathlib import Path

logger = logging.getLogger(__name__)

# Resolve absolute path to backend/reports directory
REPORTS_DIR = os.path.join(str(Path(__file__).resolve().parents[4]), "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)

def structure_report_node(state: AgentState) -> dict:
    """Consumes the markdown analysis and wraps it in a boilerplate HTML template for PDF rendering."""
    logger.info("Executing Report Agent Subgraph: structure_report_node")
    analysis_md = state.get("analysis_result", "No analysis provided.")
    session_id = state.get("session_id", "default_session")
    
    # Convert markdown analysis to HTML
    html_content = markdown.markdown(analysis_md, extensions=['tables', 'fenced_code'])
    
    # Wrap in basic CSS/HTML boilerplate tailored for xhtml2pdf styling
    structured_html = f"""
    <html>
    <head>
        <style>
            @page {{
                size: a4 portrait;
                @frame header_frame {{
                    -pdf-frame-content: header_content;
                    left: 50pt; width: 512pt; top: 30pt; height: 40pt;
                }}
                @frame content_frame {{
                    left: 50pt; width: 512pt; top: 80pt; height: 692pt;
                }}
                @frame footer_frame {{
                    -pdf-frame-content: footer_content;
                    left: 50pt; width: 512pt; top: 792pt; height: 20pt;
                }}
            }}
            body {{
                font-family: Helvetica, Arial, sans-serif;
                font-size: 11pt;
                color: #333333;
            }}
            h1, h2, h3 {{
                color: #2c3e50;
            }}
            .header {{
                text-align: right;
                font-size: 9pt;
                color: #7f8c8d;
                border-bottom: 1px solid #bdc3c7;
                padding-bottom: 5px;
            }}
            .footer {{
                text-align: center;
                font-size: 8pt;
                color: #95a5a6;
                border-top: 1px solid #bdc3c7;
                padding-top: 5px;
            }}
            code {{
                background-color: #f8f9fa;
                padding: 2px 4px;
                border-radius: 4px;
                font-family: monospace;
            }}
            pre {{
                background-color: #f8f9fa;
                padding: 10px;
                border: 1px solid #e9ecef;
                white-space: pre-wrap;
            }}
        </style>
    </head>
    <body>
        <div id="header_content" class="header">
            ImmersiveRAG Dynamic Orchestrator | Session ID: {session_id}
        </div>
        
        <h1>Analytical Intelligence Report</h1>
        <hr/>
        {html_content}
        
        <div id="footer_content" class="footer">
            Generated Automatically by LangGraph Report Agent Subgraph — Page <pdf:pagenumber> of <pdf:pagecount>
        </div>
    </body>
    </html>
    """
    
    # Temporarily store HTML in final_report key to pass it to the generator node
    return {"final_report": structured_html}

def generate_pdf_node(state: AgentState) -> dict:
    """Takes the structured HTML and physically renders it to disk as a complete PDF report."""
    logger.info("Executing Report Agent Subgraph: generate_pdf_node")
    html_data = state.get("final_report", "")
    session_id = state.get("session_id", "default_session")
    
    # If the report is somehow empty, increment step safely and gracefully exit
    if not html_data.strip().startswith("<html>"):
        logger.warning("No structured HTML found for PDF generation.")
        next_step = state.get("current_step_index", 0) + 1
        return {"current_step_index": next_step}
        
    output_path = os.path.join(REPORTS_DIR, f"report_{session_id}.pdf")
    
    try:
        # PISA requires a binary write handle
        with open(output_path, "w+b") as result_file:
            pisa_status = pisa.CreatePDF(html_data, dest=result_file)
            
        if pisa_status.err:
            logger.error("xhtml2pdf encountered errors during generation.")
            return {"final_report": f"PDF Generation Error. Check logs."}
            
        logger.info(f"Successfully generated offline PDF report at: {output_path}")
        
        # Overwrite the HTML in state with the output path and step up graph execution
        next_step = state.get("current_step_index", 0) + 1
        return {
            "final_report": output_path,
            "current_step_index": next_step
        }
    except Exception as e:
        logger.error(f"Failed to generate PDF: {e}")
        return {"final_report": f"Crash during PDF extraction: {str(e)}"}

def build_report_subgraph() -> StateGraph:
    graph = StateGraph(AgentState)
    
    graph.add_node("structure_report", structure_report_node)
    graph.add_node("generate_pdf", generate_pdf_node)
    
    graph.set_entry_point("structure_report")
    graph.add_edge("structure_report", "generate_pdf")
    graph.add_edge("generate_pdf", END)
    
    return graph.compile()

report_subgraph = build_report_subgraph()
