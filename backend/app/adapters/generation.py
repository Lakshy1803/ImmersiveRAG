from __future__ import annotations

from abc import ABC, abstractmethod
from base64 import b64encode
from pathlib import Path
from typing import Iterable

from openai import OpenAI

from app.core.config import Settings
from app.models import EvidenceModality, RetrievalResult


class GenerationProvider(ABC):
    @abstractmethod
    def generate(self, question: str, evidence: list[RetrievalResult]) -> str:
        raise NotImplementedError


class ExtractiveGenerationProvider(GenerationProvider):
    def generate(self, question: str, evidence: list[RetrievalResult]) -> str:
        del question
        snippets = [item.text.strip() for item in _unique_text_evidence(evidence, limit=3)]
        if not snippets:
            return "The retrieved visual evidence is relevant, but there was no extractable text to summarize."
        return " ".join(snippets)[:900]


class OpenAICompatibleGenerationProvider(GenerationProvider):
    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        base_url: str | None,
        temperature: float,
        max_completion_tokens: int,
    ) -> None:
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        self.temperature = temperature
        self.max_completion_tokens = max_completion_tokens

    def generate(self, question: str, evidence: list[RetrievalResult]) -> str:
        text_evidence = list(_unique_text_evidence(evidence, limit=4))
        image_evidence = list(_unique_image_evidence(evidence, limit=2))
        evidence_block = "\n\n".join(
            _format_evidence_line(index + 1, item)
            for index, item in enumerate([*text_evidence, *image_evidence])
        )
        content: list[dict] = [
            {
                "type": "text",
                "text": (
                    "Answer the question using only the provided evidence.\n"
                    "Prefer the text evidence for precise claims and use the images as visual support.\n"
                    "If the evidence is insufficient, say that explicitly.\n"
                    "When you make a claim, cite the supporting evidence tags like [E1].\n\n"
                    f"Question:\n{question}\n\nEvidence:\n{evidence_block}"
                ),
            }
        ]
        for item in image_evidence:
            if not item.image_path:
                continue
            image_path = Path(item.image_path)
            if not image_path.exists():
                continue
            mime = "image/png" if image_path.suffix.lower() == ".png" else "image/jpeg"
            b64 = b64encode(image_path.read_bytes()).decode("ascii")
            content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:{mime};base64,{b64}"},
                }
            )
        response = self.client.chat.completions.create(
            model=self.model,
            temperature=self.temperature,
            max_completion_tokens=self.max_completion_tokens,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a grounded multimodal RAG assistant. "
                        "Answer only from the provided evidence, do not invent facts, "
                        "and preserve citation tags from the evidence list."
                    ),
                },
                {
                    "role": "user",
                    "content": content,
                },
            ],
        )
        return (response.choices[0].message.content or "").strip()


def build_generation_provider(settings: Settings) -> GenerationProvider:
    if settings.generation_provider == "openai":
        api_key = settings.generation_api_key or settings.openai_api_key
        base_url = settings.generation_base_url or settings.openai_base_url
        if not api_key:
            raise ValueError(
                "IMMERSIVE_RAG_GENERATION_API_KEY or IMMERSIVE_RAG_OPENAI_API_KEY is required when generation_provider=openai"
            )
        return OpenAICompatibleGenerationProvider(
            api_key=api_key,
            base_url=base_url,
            model=settings.generation_model,
            temperature=settings.generation_temperature,
            max_completion_tokens=settings.generation_max_completion_tokens,
        )
    return ExtractiveGenerationProvider()


def _evidence_identity(item: RetrievalResult) -> tuple[str, int, str | None, str | None, str]:
    return (
        item.document_id,
        item.page_number,
        item.citation.chunk_id,
        item.citation.image_id,
        item.modality.value,
    )


def _unique_text_evidence(evidence: Iterable[RetrievalResult], limit: int) -> list[RetrievalResult]:
    return _unique_evidence(
        (item for item in evidence if item.modality == EvidenceModality.TEXT and item.text.strip()),
        limit=limit,
    )


def _unique_image_evidence(evidence: Iterable[RetrievalResult], limit: int) -> list[RetrievalResult]:
    return _unique_evidence(
        (item for item in evidence if item.modality == EvidenceModality.IMAGE),
        limit=limit,
    )


def _unique_evidence(evidence: Iterable[RetrievalResult], limit: int) -> list[RetrievalResult]:
    unique: list[RetrievalResult] = []
    seen: set[tuple[str, int, str | None, str | None, str]] = set()
    for item in evidence:
        key = _evidence_identity(item)
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
        if len(unique) >= limit:
            break
    return unique


def _format_evidence_line(index: int, item: RetrievalResult) -> str:
    tag = f"[E{index}]"
    modality = item.modality.value
    locator = f"{item.document_name} p.{item.page_number}"
    detail = item.text.strip() or "visual evidence"
    return f"{tag} ({modality}) {locator}: {detail}"
