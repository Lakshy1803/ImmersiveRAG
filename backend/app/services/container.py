from __future__ import annotations

from contextlib import asynccontextmanager
from functools import lru_cache

from app.adapters.embeddings import EmbeddingProvider, build_embedding_provider
from app.adapters.generation import ExtractiveGenerationProvider, GenerationProvider, build_generation_provider
from app.adapters.metadata_store import SqliteMetadataStore
from app.adapters.object_store import LocalObjectStore
from app.adapters.vector_store import LlamaQdrantMultiModalIndex, build_qdrant_client
from app.core.config import Settings, settings
from app.services.answering import AnswerService
from app.services.diagnostics import DiagnosticsService
from app.services.ingestion import IngestionService
from app.services.parsing import FallbackParser, LlamaParseParser, Parser
from app.services.retrieval import RetrievalService


class ServiceContainer:
    def __init__(
        self,
        *,
        app_settings: Settings | None = None,
        parser: Parser | None = None,
        embedding_provider: EmbeddingProvider | None = None,
        generation_provider: GenerationProvider | None = None,
    ) -> None:
        self.settings = app_settings or settings
        self.initialization_errors: list[str] = []
        self.settings.data_dir.mkdir(parents=True, exist_ok=True)
        self.object_store = LocalObjectStore(self.settings.uploads_dir)
        self.metadata_store = SqliteMetadataStore(self.settings.database_path)
        self.embedding_provider = embedding_provider or build_embedding_provider(self.settings)
        if generation_provider is not None:
            self.generation_provider = generation_provider
        else:
            try:
                self.generation_provider = build_generation_provider(self.settings)
            except Exception as exc:
                self.generation_provider = ExtractiveGenerationProvider()
                self.initialization_errors.append(f"generation_provider: {exc}")
        if parser is not None:
            self.parser = parser
        else:
            fallback_parser = FallbackParser(self.settings)
            try:
                self.parser = LlamaParseParser(self.settings, fallback=fallback_parser)
            except Exception as exc:
                self.parser = fallback_parser
                self.initialization_errors.append(f"parser_provider: {exc}")
        self.qdrant_client = build_qdrant_client(self.settings)
        self.index = LlamaQdrantMultiModalIndex(self.qdrant_client, self.embedding_provider, self.settings)
        self.ingestion = IngestionService(self.object_store, self.metadata_store, self.parser)
        self.retrieval = RetrievalService(self.metadata_store, self.index)
        self.answering = AnswerService(self.retrieval, self.generation_provider, self.settings)
        self.diagnostics = DiagnosticsService(self.settings, self.qdrant_client, self.initialization_errors)

    def close(self) -> None:
        self.qdrant_client.close()


@lru_cache(maxsize=1)
def get_container() -> ServiceContainer:
    return ServiceContainer()


@asynccontextmanager
async def app_lifespan(app):
    del app
    try:
        yield
    finally:
        if get_container.cache_info().currsize:
            get_container().close()
            get_container.cache_clear()
