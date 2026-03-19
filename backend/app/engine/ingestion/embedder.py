from typing import List, Optional
import os
import logging
from app.core.config import config
from openai import OpenAI

logger = logging.getLogger(__name__)

# Cache the local fastembed model so it doesn't load every time
_fastembed_model = None

def get_corporate_embeddings(texts: List[str], embedding_mode: str = "local_fastembed") -> List[List[float]]:
    """
    Calls the configurable Corporate API for embeddings using the OpenAI client spec.
    For local development, it falls back to FastEmbed if the API keys aren't set or extraction_mode explicitly says so.
    """
    if not texts:
        return []
        
    api_key = config.embedding_api_key
    base_url = config.embedding_base_url
    model = config.embedding_model
    
    # If the user requested local mode, or hasn't configured the corporate endpoint yet
    if embedding_mode == "local_fastembed" or not api_key:
        logger.info("Corporate API Key missing. Using FastEmbed locally for embeddings.")
        global _fastembed_model
        if _fastembed_model is None:
            # Handle SSL verification bypass specifically for the first-time model download
            if config.bypass_ssl_verify:
                import ssl
                logger.warning("Bypassing SSL verification for local model download (PwC compliance).")
                ssl._create_default_https_context = ssl._create_unverified_context
                
            from fastembed import TextEmbedding
            # BAAI/bge-small-en-v1.5 has an embedding dimension of 384
            _fastembed_model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
            
        # FastEmbed returns a generator of numpy arrays, we convert to list of floats
        embeddings_generator = _fastembed_model.embed(texts)
        return [vector.tolist() for vector in embeddings_generator]

    # Otherwise, use the corporate API via the OpenAI client wrapper (STRICT SSL)
    logger.info(f"Using corporate API (OpenAI client) with model: {model}")
    client_kwargs = {"api_key": api_key}
    
    if base_url:
        client_kwargs["base_url"] = base_url

    client = OpenAI(**client_kwargs)
    
    try:
        response = client.embeddings.create(
            input=texts,
            model=model
        )
        # Extract and return the embeddings from the response data
        return [data.embedding for data in response.data]
    except Exception as e:
        logger.error(f"Failed to fetch corporate embeddings via OpenAI client: {e}")
        raise e
