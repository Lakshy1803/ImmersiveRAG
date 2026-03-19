"""
Official OpenAI-compatible client for ImmersiveRAG.
Returns a singleton AsyncOpenAI client instance.
"""
import logging
from openai import AsyncOpenAI
from app.core.config import config

logger = logging.getLogger(__name__)

_llm_client = None

def get_llm_client():
    """Returns a cached synchronous OpenAI instance configured from .env settings."""
    global _llm_client
    if _llm_client is not None:
        return _llm_client

    from openai import OpenAI
    api_key = config.llm_api_key
    if not api_key:
        raise RuntimeError("IMMERSIVE_RAG_LLM_API_KEY is not set.")

    client_kwargs = {"api_key": api_key}
    if config.llm_base_url:
        client_kwargs["base_url"] = config.llm_base_url

    # Scoped SSL Bypass (only for Qdrant/Model downloads, not LLM by default)
    # But if users at PwC need it, they can enable it globally in AppConfig
    if config.bypass_ssl_verify:
        import httpx
        client_kwargs["http_client"] = httpx.Client(verify=False)

    _llm_client = OpenAI(**client_kwargs)
    logger.info(f"Synchronous LLM client ready (model: {config.llm_model})")
    return _llm_client
