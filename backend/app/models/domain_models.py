from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class JobStatus(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    EMBEDDING_AND_INDEXING = "embedding_and_indexing"
    FAILED = "failed"
    COMPLETE = "complete"


class EvidenceModality(str, Enum):
    TEXT = "text"
    IMAGE = "image"


class DocumentIngestRequest(BaseModel):
    source_path: str
    filename: str
    content_type: str
    tenant_id: str = "default"
    collection_id: str = "default"
    metadata: dict[str, str] = Field(default_factory=dict)
    replace_existing: bool = True
    extraction_mode: Literal["local_markdown", "cloud_llamaparse"] = "local_markdown"
    embedding_mode: Literal["local_fastembed", "cloud_openai"] = "local_fastembed"


class IngestionJob(BaseModel):
    job_id: str = Field(default_factory=lambda: f"job_{uuid4().hex}")
    status: JobStatus = JobStatus.QUEUED
    request: DocumentIngestRequest
    document_id: str | None = None
    error: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class AgentContextSession(BaseModel):
    session_id: str
    agent_id: str
    created_at: datetime = Field(default_factory=utc_now)
    last_accessed_at: datetime = Field(default_factory=utc_now)
    interaction_count: int = 0
