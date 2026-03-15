from __future__ import annotations

from abc import ABC, abstractmethod
from collections import Counter
from math import sqrt
from typing import Iterable

from fastembed import TextEmbedding
from openai import OpenAI

from app.core.config import Settings


def _normalize(vector: list[float]) -> list[float]:
    norm = sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [value / norm for value in vector]


class EmbeddingProvider(ABC):
    def __init__(self) -> None:
        self._vector_size: int | None = None

    @property
    def vector_size(self) -> int:
        if self._vector_size is None:
            self._vector_size = len(self.embed_query("dimension probe"))
        return self._vector_size

    @abstractmethod
    def embed_texts(self, texts: Iterable[str]) -> list[list[float]]:
        raise NotImplementedError

    def embed_query(self, text: str) -> list[float]:
        return self.embed_texts([text])[0]


class FastEmbedProvider(EmbeddingProvider):
    def __init__(self, model_name: str, cache_dir: str | None = None) -> None:
        super().__init__()
        self.model = TextEmbedding(model_name=model_name, cache_dir=cache_dir)

    def embed_texts(self, texts: Iterable[str]) -> list[list[float]]:
        return [list(vector) for vector in self.model.embed(list(texts))]


class OpenAIEmbeddingProvider(EmbeddingProvider):
    def __init__(self, api_key: str, model_name: str, base_url: str | None = None) -> None:
        super().__init__()
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model_name = model_name

    def embed_texts(self, texts: Iterable[str]) -> list[list[float]]:
        payload = list(texts)
        response = self.client.embeddings.create(model=self.model_name, input=payload)
        return [list(item.embedding) for item in response.data]


class HashEmbeddingProvider(EmbeddingProvider):
    """Cheap deterministic provider used for tests."""

    def __init__(self, dimensions: int = 32) -> None:
        super().__init__()
        self._vector_size = dimensions

    def embed_texts(self, texts: Iterable[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for text in texts:
            buckets = [0.0] * self.vector_size
            for token, count in Counter(text.lower().split()).items():
                buckets[hash(token) % self.vector_size] += float(count)
            vectors.append(_normalize(buckets))
        return vectors


def build_embedding_provider(settings: Settings) -> EmbeddingProvider:
    if settings.embedding_provider == "openai":
        if not settings.openai_api_key:
            raise ValueError("IMMERSIVE_RAG_OPENAI_API_KEY is required when embedding_provider=openai")
        return OpenAIEmbeddingProvider(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
            model_name=settings.openai_embedding_model,
        )
    cache_dir = str(settings.embedding_cache_dir) if settings.embedding_cache_dir else None
    return FastEmbedProvider(model_name=settings.embedding_model, cache_dir=cache_dir)
