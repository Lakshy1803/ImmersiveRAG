import logging
import uuid
import os
from langgraph.graph import StateGraph, END
from app.engine.agents.state import AgentState
from app.engine.ingestion.parser import run_llamaparse_extraction
from app.engine.ingestion.chunker import chunk_markdown_content
from app.engine.ingestion.embedder import get_corporate_embeddings
from app.storage.vector_db import get_qdrant_client
from qdrant_client.http.models import PointStruct

logger = logging.getLogger(__name__)

async def file_type_routing_node(state: AgentState) -> dict:
    """Evaluates uploaded docs and preps metadata for conditional routing."""
    logger.info("Executing Document Agent Subgraph: file_type_routing_node")
    docs = state.get("uploaded_docs", [])
    if not docs:
        logger.warning("No docs found in state. Injecting a mock PDF payload for LangGraph testing.")
        return {"uploaded_docs": [{"filename": "mock.pdf", "path": "mock.pdf", "type": "pdf"}]}
    return {}

def route_parser(state: AgentState) -> str:
    """Conditional edge router based on file extension/type."""
    docs = state.get("uploaded_docs", [])
    if not docs:
        return "parse_pdf" 
        
    # In Phase 1 we assume processing one file per batch for simplicity, or iterate outside
    file_type = docs[0].get("type", "pdf").lower()
    
    if file_type == "csv":
        return "parse_csv"
    elif file_type == "png" or file_type == "image":
        return "parse_png"
    
    return "parse_pdf"

async def parse_pdf_node(state: AgentState) -> dict:
    logger.info("Executing Document Agent Subgraph: parse_pdf_node")
    docs = state.get("uploaded_docs", [])
    path = docs[0].get("path", "mock.pdf")
    
    try:
        pages = await run_llamaparse_extraction(path)
    except FileNotFoundError:
        logger.warning(f"File {path} not found locally, using safe fallback mock text.")
        pages = [{"text": "Mock PDF execution. The Master Orchestrator reached the PDF parser correctly.", "metadata": {"page": "1"}}]
        
    return {"document_chunks": pages} # passing raw pages to chunker

async def parse_csv_node(state: AgentState) -> dict:
    logger.info("Executing Document Agent Subgraph: parse_csv_node")
    return {"document_chunks": [{"text": "Mock CSV tabular parsing logic reached.", "metadata": {"row": "1", "type": "csv"}}]}

async def parse_png_node(state: AgentState) -> dict:
    logger.info("Executing Document Agent Subgraph: parse_png_node")
    docs = state.get("uploaded_docs", [])
    path = docs[0].get("path", "mock.png")
    
    from app.engine.document_processing.ocr_parser import extract_text_from_image
    
    if os.path.exists(path):
        text = extract_text_from_image(path, use_easyocr=False)
        pages = [{"text": text, "metadata": {"page": "1", "type": "png"}}]
    else:
        logger.warning(f"File {path} not found locally, using safe fallback mock text.")
        pages = [{"text": "Mock PNG OCR text. Ensure Tesseract/EasyOCR is configured.", "metadata": {"type": "png"}}]
        
    return {"document_chunks": pages}

def chunk_node(state: AgentState) -> dict:
    logger.info("Executing Document Agent Subgraph: chunk_node")
    raw_pages = state.get("document_chunks", [])
    filename = state.get("uploaded_docs", [{"filename": "mock.pdf"}])[0].get("filename", "mock")
    
    if raw_pages:
        chunks = chunk_markdown_content(raw_pages, filename)
    else:
        chunks = []
        
    return {"document_chunks": chunks}

def vector_db_insert_node(state: AgentState) -> dict:
    logger.info("Executing Document Agent Subgraph: vector_db_insert_node")
    chunks = state.get("document_chunks", [])
    agent_id = state.get("agent_id", "default_setup")
    
    next_step = state.get("current_step_index", 0) + 1
    
    if not chunks:
        logger.warning("No document chunks generated. Skipping Qdrant insertion.")
        return {"current_step_index": next_step}
        
    # Generate Embeddings
    texts = [c["text"] for c in chunks]
    embeddings = get_corporate_embeddings(texts)
    
    # Insert to Qdrant Core Collection
    client = get_qdrant_client()
    points = []
    
    for i, chunk in enumerate(chunks):
        points.append(PointStruct(
            id=uuid.uuid4().hex,
            vector=embeddings[i],
            payload={
                "text": chunk["text"],
                "metadata": chunk["metadata"],
                "agent_id": agent_id
            }
        ))
        
    client.upsert(
        collection_name="rag_text",
        points=points
    )
    logger.info(f"Successfully upserted {len(points)} vectors into Qdrant for Agent: {agent_id}.")
    
    return {"current_step_index": next_step}

def build_document_subgraph() -> StateGraph:
    graph = StateGraph(AgentState)
    
    graph.add_node("routing", file_type_routing_node)
    graph.add_node("parse_pdf", parse_pdf_node)
    graph.add_node("parse_csv", parse_csv_node)
    graph.add_node("parse_png", parse_png_node)
    graph.add_node("chunk", chunk_node)
    graph.add_node("insert", vector_db_insert_node)
    
    graph.set_entry_point("routing")
    
    # Conditional Edges for Parser selection
    graph.add_conditional_edges("routing", route_parser)
    
    # All parsers converge back to semantic chunking
    graph.add_edge("parse_pdf", "chunk")
    graph.add_edge("parse_csv", "chunk")
    graph.add_edge("parse_png", "chunk")
    
    # Finalize insertion
    graph.add_edge("chunk", "insert")
    graph.add_edge("insert", END)
    
    return graph.compile()

document_subgraph = build_document_subgraph()
