"""
Official OpenAI Client helper.
Returns a singleton synchronous OpenAI client instance.
Supports runtime reconfiguration via reset_llm_client().
"""
import logging
from app.core.config import config

logger = logging.getLogger(__name__)

_llm_client = None

def get_llm_client():
    """Returns a cached synchronous OpenAI instance configured from .env / runtime settings."""
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

    if config.bypass_ssl_verify:
        import httpx
        client_kwargs["http_client"] = httpx.Client(verify=False)

    _llm_client = OpenAI(**client_kwargs)
    logger.info(f"Synchronous LLM client ready (model: {config.llm_model})")
    return _llm_client


def reset_llm_client():
    """
    Drops the cached client so the next call to get_llm_client()
    picks up the latest config values (api_key, base_url, model).
    Call this after updating config.llm_* at runtime.
    """
    global _llm_client
    _llm_client = None
    logger.info("LLM client singleton reset — will reinitialise on next request.")
