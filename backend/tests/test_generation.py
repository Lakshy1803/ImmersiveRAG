from __future__ import annotations

from app.adapters.generation import ExtractiveGenerationProvider
from app.models import Citation, EvidenceModality, RetrievalResult


def test_extractive_generation_deduplicates_repeated_text_evidence() -> None:
    provider = ExtractiveGenerationProvider()
    shared_citation = Citation(
        document_id="doc_1",
        document_name="report.pdf",
        page_number=1,
        chunk_id="txt_1",
        snippet="Revenue increased in Europe.",
    )
    evidence = [
        RetrievalResult(
            result_id="lexical_txt_1",
            document_id="doc_1",
            document_name="report.pdf",
            page_number=1,
            modality=EvidenceModality.TEXT,
            score=0.9,
            text="Revenue increased in Europe.",
            citation=shared_citation,
            retriever="lexical",
        ),
        RetrievalResult(
            result_id="dense_txt_1",
            document_id="doc_1",
            document_name="report.pdf",
            page_number=1,
            modality=EvidenceModality.TEXT,
            score=0.8,
            text="Revenue increased in Europe.",
            citation=shared_citation,
            retriever="multimodal",
        ),
    ]

    answer = provider.generate("What happened in Europe?", evidence)

    assert answer == "Revenue increased in Europe."
