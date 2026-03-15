from __future__ import annotations

from statistics import mean

from app.adapters.generation import GenerationProvider
from app.core.config import Settings
from app.models import AnswerResponse, QueryRequest
from app.services.retrieval import RetrievalService


class AnswerService:
    def __init__(
        self,
        retrieval_service: RetrievalService,
        generation_provider: GenerationProvider,
        settings: Settings,
    ) -> None:
        self.retrieval_service = retrieval_service
        self.generation_provider = generation_provider
        self.settings = settings

    def answer(self, query: QueryRequest) -> AnswerResponse:
        evidence = self.retrieval_service.retrieve(
            query.question,
            query.tenant_id,
            query.collection_id,
            min(query.top_k, self.settings.max_evidence_items),
        )
        if not evidence:
            return AnswerResponse(
                answer="I could not find supporting evidence in the indexed corpus.",
                grounded=False,
                confidence=0.0,
                guardrails=["no_evidence"],
            )

        confidence = mean(item.score for item in evidence)
        citations = [item.citation for item in evidence]
        if confidence < self.settings.min_supported_score:
            return AnswerResponse(
                answer="I found weak evidence, so I am not providing a definitive answer.",
                citations=citations,
                evidence=evidence,
                grounded=False,
                confidence=confidence,
                guardrails=["low_confidence_retrieval"],
            )

        guardrails: list[str] = []
        try:
            summary = self.generation_provider.generate(query.question, evidence)
        except Exception:
            summary = " ".join(item.text.strip() for item in evidence[:3] if item.text.strip())[:900]
            guardrails.append("generation_fallback")
        return AnswerResponse(
            answer=summary,
            citations=citations,
            evidence=evidence,
            grounded=True,
            confidence=confidence,
            guardrails=guardrails,
        )
