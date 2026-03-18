"""
Thin wrapper around LangChain's ChatOpenAI using the company-provided API keys.
Cached as a singleton to avoid re-initialization on every request.
"""
import logging
from langchain_openai import ChatOpenAI
from app.core.config import config

logger = logging.getLogger(__name__)

_llm_instance: ChatOpenAI | None = None


def get_llm() -> ChatOpenAI:
    """Returns a cached ChatOpenAI instance configured from .env settings."""
    global _llm_instance
    if _llm_instance is not None:
        return _llm_instance

    api_key = config.llm_api_key
    if not api_key:
        raise RuntimeError(
            "IMMERSIVE_RAG_LLM_API_KEY is not set. "
            "Please configure your company LLM API key in backend/.env"
        )

    kwargs: dict = {
        "api_key": api_key,
        "model": config.llm_model,
        "max_tokens": config.llm_max_answer_tokens,
        "temperature": 0.3,  # Low temp for precise corporate answers
        "streaming": True,   # Enable streaming for real-time token delivery
    }

    if config.llm_base_url:
        kwargs["base_url"] = config.llm_base_url

    if config.bypass_ssl_verify:
        import httpx
        logger.warning("Bypassing SSL verification for LLM client.")
        # Note: ChatOpenAI uses httpx internally and accepts a custom client
        kwargs["http_client"] = httpx.Client(verify=False)

    _llm_instance = ChatOpenAI(**kwargs)
    logger.info(f"LLM client initialized: model={config.llm_model}")
    return _llm_instance
