from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
from pathlib import Path

# Derive absolute backend root regardless of where uvicorn is launched from
# config.py lives at: backend/app/core/config.py  =>  .parent=core, .parent=app, .parent=backend
_BACKEND_ROOT = Path(__file__).parent.parent.parent.resolve()
_DATA_DIR = _BACKEND_ROOT / "data"

class AppConfig(BaseSettings):
    # API configuration
    api_title: str = "ImmersiveRAG Shared Context API"
    api_version: str = "v1.0"

    # Storage and DB paths
    data_dir: str = str(_DATA_DIR)
    sqlite_db_path: str = f"sqlite:///{_DATA_DIR / 'rag.db'}"
    qdrant_path: str = str(_DATA_DIR / "qdrant")
    qdrant_url: Optional[str] = Field(default=None, env="IMMERSIVE_RAG_QDRANT_URL")

    # Ingestion Configuration
    llamaparse_api_key: Optional[str] = Field(default=None, env="IMMERSIVE_RAG_LLAMA_PARSE_API_KEY")
    tesseract_cmd_path: Optional[str] = Field(default=None, env="IMMERSIVE_RAG_TESSERACT_CMD_PATH")

    # ── Company Embedding API (OpenAI-compatible) ──────────────────────────
    # If embedding_api_key is unset → falls back to local FastEmbed (384-dim)
    embedding_provider: str = Field(default="corporate_api", env="IMMERSIVE_RAG_EMBEDDING_PROVIDER")
    embedding_model: str = Field(default="text-embedding-3-small", env="IMMERSIVE_RAG_EMBEDDING_MODEL")
    embedding_api_key: Optional[str] = Field(default=None, env="IMMERSIVE_RAG_OPENAI_API_KEY")
    embedding_base_url: Optional[str] = Field(default=None, env="IMMERSIVE_RAG_OPENAI_BASE_URL")

    # ── Company LLM Generation API (for agent answer synthesis / future use) ──
    # These are not used in the base retrieval-only mode.
    # Wire these into your LangGraph node when you need generated answers.
    llm_api_key: Optional[str] = Field(default=None, env="IMMERSIVE_RAG_LLM_API_KEY")
    llm_base_url: Optional[str] = Field(default=None, env="IMMERSIVE_RAG_LLM_BASE_URL")
    llm_model: str = Field(default="gpt-4o", env="IMMERSIVE_RAG_LLM_MODEL")

    # Memory Management
    max_context_tokens: int = Field(default=4000, description="Max tokens returned to the agent")
    session_timeout_minutes: int = Field(default=30)
    sliding_window_size: int = Field(default=10, description="Max recent queries kept in session memory")

    # Agent Generation Budget
    llm_max_answer_tokens: int = Field(default=512, description="Max tokens for LLM answer generation")
    history_summary_max_tokens: int = Field(default=256, description="Max tokens for rolling conversation summary")

    # Security / Networking
    # Set to True to bypass SSL certificate verification (e.g. corporate proxy issues)
    bypass_ssl_verify: bool = Field(default=False, env="IMMERSIVE_RAG_BYPASS_SSL_VERIFY")

    class Config:
        # Absolute path so .env is found regardless of where uvicorn is launched from
        env_file = str(_BACKEND_ROOT / ".env")
        env_prefix = "IMMERSIVE_RAG_"
        extra = "ignore"

config = AppConfig()
