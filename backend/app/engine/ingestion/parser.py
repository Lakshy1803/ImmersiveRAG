from llama_parse import LlamaParse
from app.core.config import config
import os
import logging

logger = logging.getLogger(__name__)

async def run_llamaparse_extraction(file_path: str) -> str:
    """
    Runs LlamaParse on the given file path.
    Pre-condition: User has confirmed VPN is OFF, allowing external call to llama-parse.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
        
    if not config.llamaparse_api_key:
        logger.warning("IMMERSIVE_RAG_LLAMA_PARSE_API_KEY missing. Returning simulated mock parser markdown.")
        import asyncio
        await asyncio.sleep(2) # simulate parsing delay
        return f"# MOCK PARSED DOCUMENT: {os.path.basename(file_path)}\n\nThis is a simulated document chunk generated because LlamaParse API keys were missing. It contains enough content to verify the embedding generation and Qdrant ingestion stages."
        
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
    
    # We receive LangChain/LlamaIndex document objects, we concatenate the text block
    full_markdown = "\n\n".join([doc.text for doc in documents])
    return full_markdown
