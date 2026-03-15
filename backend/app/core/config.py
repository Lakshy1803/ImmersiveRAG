from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="IMMERSIVE_RAG_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "ImmersiveRAG"
    data_dir: Path = Field(default_factory=lambda: Path(__file__).resolve().parents[2] / "data")
    uploads_dir_name: str = "uploads"
    extracted_images_dir_name: str = "images"
    database_name: str = "rag.db"

    max_file_size_bytes: int = 20 * 1024 * 1024
    max_evidence_items: int = 8
    min_supported_score: float = 0.18
    chunk_size: int = 400
    chunk_overlap: int = 50
    min_image_side_pixels: int = 32

    parser_provider: Literal["llamaparse"] = "llamaparse"
    llama_parse_api_key: str | None = None
    llama_parse_result_type: Literal["markdown", "text"] = "markdown"
    llama_parse_language: str = "en"
    llama_parse_num_workers: int = 1
    llama_parse_fast_mode: bool = False
    llama_parse_premium_mode: bool = False
    llama_parse_verbose: bool = False
    llama_parse_do_ocr: bool = True
    llama_parse_confidence_threshold: float = 0.65
    embedding_provider: Literal["fastembed", "openai"] = "fastembed"
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_cache_dir: Path | None = None
    openai_api_key: str | None = None
    openai_base_url: str | None = None
    openai_embedding_model: str = "text-embedding-3-small"

    generation_provider: Literal["extractive", "openai"] = "extractive"
    generation_model: str = "openai/gpt-oss-120b"
    generation_api_key: str | None = None
    generation_base_url: str | None = None
    generation_temperature: float = 0.2
    generation_max_completion_tokens: int = 1200

    qdrant_location: str | None = None
    qdrant_url: str | None = None
    qdrant_api_key: str | None = None
    qdrant_path: Path | None = None
    qdrant_text_collection: str = "rag_text"
    qdrant_image_collection: str = "rag_image"
    multimodal_text_top_k: int = 5
    multimodal_image_top_k: int = 5

    @property
    def uploads_dir(self) -> Path:
        return self.data_dir / self.uploads_dir_name

    @property
    def extracted_images_dir(self) -> Path:
        return self.data_dir / self.extracted_images_dir_name

    @property
    def database_path(self) -> Path:
        return self.data_dir / self.database_name

    @property
    def qdrant_storage_path(self) -> Path:
        if self.qdrant_path is not None:
            return self.qdrant_path
        return self.data_dir / "qdrant"


settings = Settings()
