from llama_parse import LlamaParse
from app.core.config import config
import os
import logging

logger = logging.getLogger(__name__)

async def run_llamaparse_extraction(file_path: str) -> list[dict]:
    """
    Runs LlamaParse on the given file path.
    Pre-condition: User has confirmed VPN is OFF, allowing external call to llama-parse.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
        
    if not config.llamaparse_api_key:
        logger.info("IMMERSIVE_RAG_LLAMA_PARSE_API_KEY missing. Falling back to local PyMuPDF + Tesseract OCR pipeline.")
        from app.engine.document_processing.ocr_parser import extract_text_from_pdf_locally
        return extract_text_from_pdf_locally(file_path)
        
    logger.info(f"Starting LlamaParse extraction for {file_path} with VPN OFF assumed.")
    
    # We use premium mode to get good structure mapping
    parser = LlamaParse(
        api_key=config.llamaparse_api_key,
        result_type="markdown",
        premium_mode=True,
        verbose=True
    )
    
    # LlamaParse handles asynchronous ingestion internally
    documents = await parser.aload_data(file_path)
    
    # We receive LangChain/LlamaIndex document objects
    results = []
    for doc in documents:
        # LlamaParse metadata contains 'page_label' or 'page_number' usually
        meta = doc.metadata if hasattr(doc, "metadata") and doc.metadata else {}
        page = meta.get("page_label", meta.get("page_number", "1"))
        results.append({
            "text": doc.text,
            "metadata": {"page": str(page)}
        })

    return results
