from __future__ import annotations

import os

from pydantic import BaseModel, Field

from app.core.config import Settings


class DiagnosticItem(BaseModel):
    name: str
    ok: bool
    detail: str


class DiagnosticsReport(BaseModel):
    status: str
    parser_provider: str
    embedding_provider: str
    generation_provider: str
    checks: list[DiagnosticItem] = Field(default_factory=list)


class DiagnosticsService:
    def __init__(self, settings: Settings, qdrant_client, initialization_errors: list[str] | None = None) -> None:
        self.settings = settings
        self.qdrant_client = qdrant_client
        self.initialization_errors = initialization_errors or []

    def report(self) -> DiagnosticsReport:
        checks = [
            self._check_data_dir(),
            self._check_qdrant(),
            self._check_parser_config(),
            self._check_generation_config(),
            self._check_embedding_config(),
            self._check_initialization_errors(),
        ]
        status = "ok" if all(item.ok for item in checks) else "degraded"
        return DiagnosticsReport(
            status=status,
            parser_provider=self.settings.parser_provider,
            embedding_provider=self.settings.embedding_provider,
            generation_provider=self.settings.generation_provider,
            checks=checks,
        )

    def _check_data_dir(self) -> DiagnosticItem:
        exists = self.settings.data_dir.exists()
        return DiagnosticItem(
            name="data_dir",
            ok=exists,
            detail=str(self.settings.data_dir),
        )

    def _check_qdrant(self) -> DiagnosticItem:
        try:
            collections = self.qdrant_client.get_collections().collections
            return DiagnosticItem(
                name="qdrant",
                ok=True,
                detail=f"reachable, collections={len(collections)}",
            )
        except Exception as exc:
            return DiagnosticItem(
                name="qdrant",
                ok=False,
                detail=str(exc),
            )

    def _check_parser_config(self) -> DiagnosticItem:
        if self.settings.parser_provider != "llamaparse":
            return DiagnosticItem(
                name="parser_config",
                ok=True,
                detail=f"provider={self.settings.parser_provider}",
            )
        if not (self.settings.llama_parse_api_key or os.getenv("LLAMA_CLOUD_API_KEY")):
            return DiagnosticItem(
                name="parser_config",
                ok=False,
                detail="missing llama parse api key",
            )
        return DiagnosticItem(
            name="parser_config",
            ok=True,
            detail=f"provider=llamaparse result_type={self.settings.llama_parse_result_type}",
        )

    def _check_generation_config(self) -> DiagnosticItem:
        if self.settings.generation_provider != "openai":
            return DiagnosticItem(
                name="generation_config",
                ok=True,
                detail=f"provider={self.settings.generation_provider}",
            )
        api_key = self.settings.generation_api_key or self.settings.openai_api_key
        if not api_key:
            return DiagnosticItem(
                name="generation_config",
                ok=False,
                detail="missing generation/openai api key",
            )
        return DiagnosticItem(
            name="generation_config",
            ok=True,
            detail=f"provider=openai model={self.settings.generation_model}",
        )

    def _check_embedding_config(self) -> DiagnosticItem:
        if self.settings.embedding_provider != "openai":
            return DiagnosticItem(
                name="embedding_config",
                ok=True,
                detail=f"provider={self.settings.embedding_provider} model={self.settings.embedding_model}",
            )
        if not self.settings.openai_api_key:
            return DiagnosticItem(
                name="embedding_config",
                ok=False,
                detail="missing openai api key for embeddings",
            )
        return DiagnosticItem(
            name="embedding_config",
            ok=True,
            detail=f"provider=openai model={self.settings.openai_embedding_model}",
        )

    def _check_initialization_errors(self) -> DiagnosticItem:
        if not self.initialization_errors:
            return DiagnosticItem(
                name="initialization",
                ok=True,
                detail="none",
            )
        return DiagnosticItem(
            name="initialization",
            ok=False,
            detail=" | ".join(self.initialization_errors),
        )
