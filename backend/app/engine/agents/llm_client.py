"""
Official OpenAI-compatible client for ImmersiveRAG.
Returns a singleton AsyncOpenAI client instance.
"""
import logging
from openai import AsyncOpenAI
from app.core.config import config

logger = logging.getLogger(__name__)

_async_client: AsyncOpenAI | None = None
_sync_client = None # For lazy loading OpenAI sync client

def get_llm_client() -> AsyncOpenAI:
    """Returns a cached AsyncOpenAI instance configured from .env settings."""
    global _async_client
    if _async_client is not None:
        return _async_client

    api_key = config.llm_api_key
    if not api_key:
        raise RuntimeError("IMMERSIVE_RAG_LLM_API_KEY is not set.")

    client_kwargs = {"api_key": api_key}
    if config.llm_base_url:
        client_kwargs["base_url"] = config.llm_base_url

    # Handle SSL verification bypass if configured
    if config.bypass_ssl_verify:
        import httpx
        client_kwargs["http_client"] = httpx.AsyncClient(verify=False)

    _async_client = AsyncOpenAI(**client_kwargs)
    logger.info(f"AsyncOpenAI client ready (model: {config.llm_model})")
    return _async_client

def get_sync_llm_client():
    """Returns a cached sync OpenAI instance (for background tasks like Memory summary)."""
    global _sync_client
    if _sync_client is not None:
        return _sync_client

    from openai import OpenAI
    api_key = config.llm_api_key
    if not api_key:
        raise RuntimeError("IMMERSIVE_RAG_LLM_API_KEY is not set.")

    client_kwargs = {"api_key": api_key}
    if config.llm_base_url:
        client_kwargs["base_url"] = config.llm_base_url

    if config.bypass_ssl_verify:
        import httpx
        # We use a standard httpx.Client (not Async) for sync
        client_kwargs["http_client"] = httpx.Client(verify=False)

    _sync_client = OpenAI(**client_kwargs)
    logger.info("Sync OpenAI client ready.")
    return _sync_client
