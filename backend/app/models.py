from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class IngestionMode(str, Enum):
    MANUAL_UPLOAD = "manual_upload"
    BATCH = "batch"


class JobStatus(str, Enum):
    QUEUED = "queued"
    PARSING = "parsing"
    INDEXED = "indexed"
    FAILED = "failed"
    COMPLETE = "complete"


class EvidenceModality(str, Enum):
    TEXT = "text"
    IMAGE = "image"


class Citation(BaseModel):
    document_id: str
    document_name: str
    page_number: int
    chunk_id: str | None = None
    image_id: str | None = None
    bbox: list[int] | None = None
    snippet: str = ""


class DocumentIngestRequest(BaseModel):
    source_path: str
    filename: str
    content_type: str
    tenant_id: str = "default"
    collection_id: str = "default"
    ingestion_mode: IngestionMode = IngestionMode.MANUAL_UPLOAD
    metadata: dict[str, str] = Field(default_factory=dict)
    replace_existing: bool = True


class TextBlock(BaseModel):
    chunk_id: str = Field(default_factory=lambda: f"txt_{uuid4().hex}")
    page_number: int
    section: str = "body"
    text: str
    bbox: list[int] | None = None
    reading_order: int = 0
    ocr_confidence: float | None = None
    source_type: str = "text"


class ImageRegion(BaseModel):
    image_id: str = Field(default_factory=lambda: f"img_{uuid4().hex}")
    page_number: int
    path: str
    caption: str = ""
    bbox: list[int] | None = None


class PageOcrMetrics(BaseModel):
    page_number: int
    engine: str
    average_confidence: float | None = None
    min_confidence: float | None = None
    max_confidence: float | None = None
    text_cell_count: int = 0
    low_confidence_cells: int = 0


class ParsedDocument(BaseModel):
    document_id: str = Field(default_factory=lambda: f"doc_{uuid4().hex}")
    filename: str
    content_type: str
    tenant_id: str = "default"
    collection_id: str = "default"
    metadata: dict[str, str] = Field(default_factory=dict)
    text_blocks: list[TextBlock] = Field(default_factory=list)
    image_regions: list[ImageRegion] = Field(default_factory=list)
    ocr_metrics: list[PageOcrMetrics] = Field(default_factory=list)
    page_count: int = 1
    source_path: str


class RetrievalResult(BaseModel):
    result_id: str
    document_id: str
    document_name: str
    page_number: int
    modality: EvidenceModality
    score: float
    text: str = ""
    image_path: str | None = None
    citation: Citation
    retriever: Literal["lexical", "dense", "multimodal", "reranked"]


class AnswerResponse(BaseModel):
    answer: str
    citations: list[Citation] = Field(default_factory=list)
    evidence: list[RetrievalResult] = Field(default_factory=list)
    grounded: bool = True
    confidence: float = 0.0
    guardrails: list[str] = Field(default_factory=list)


class IngestionJob(BaseModel):
    job_id: str = Field(default_factory=lambda: f"job_{uuid4().hex}")
    status: JobStatus = JobStatus.QUEUED
    request: DocumentIngestRequest
    document_id: str | None = None
    error: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class QueryRequest(BaseModel):
    question: str
    tenant_id: str = "default"
    collection_id: str = "default"
    top_k: int = 5


class QueryClassification(BaseModel):
    mode: Literal["text", "image", "mixed"]
    reason: str
