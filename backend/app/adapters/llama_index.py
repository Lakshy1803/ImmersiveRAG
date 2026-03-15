from __future__ import annotations

from pathlib import Path

from app.core.warnings import silence_llama_index_pydantic_warning

silence_llama_index_pydantic_warning()

from llama_index.core.embeddings.multi_modal_base import MultiModalEmbedding
from pydantic import PrivateAttr

from app.adapters.embeddings import EmbeddingProvider


class ProviderBackedMultiModalEmbedding(MultiModalEmbedding):
    model_name: str = "provider-backed"
    _provider: EmbeddingProvider = PrivateAttr()

    def __init__(self, provider: EmbeddingProvider, **kwargs) -> None:
        super().__init__(**kwargs)
        self._provider = provider

    def _get_query_embedding(self, query: str) -> list[float]:
        return self._provider.embed_query(query)

    async def _aget_query_embedding(self, query: str) -> list[float]:
        return self._get_query_embedding(query)

    def _get_text_embedding(self, text: str) -> list[float]:
        return self._provider.embed_query(text)

    async def _aget_text_embedding(self, text: str) -> list[float]:
        return self._get_text_embedding(text)

    def _get_text_embeddings(self, texts: list[str]) -> list[list[float]]:
        return self._provider.embed_texts(texts)

    def _get_image_embedding(self, img_file_path) -> list[float]:
        return self._provider.embed_query(self._caption_for_path(img_file_path))

    async def _aget_image_embedding(self, img_file_path) -> list[float]:
        return self._get_image_embedding(img_file_path)

    def _caption_for_path(self, img_file_path) -> str:
        path = Path(str(img_file_path))
        caption_path = path.with_suffix(path.suffix + ".caption.txt")
        if caption_path.exists():
            return caption_path.read_text(encoding="utf-8").strip()
        return path.stem.replace("_", " ")
