from __future__ import annotations

from app.adapters.metadata_store import SqliteMetadataStore
from app.adapters.object_store import LocalObjectStore
from app.models import DocumentIngestRequest, IngestionJob, JobStatus
from app.services.parsing import Parser


class IngestionService:
    def __init__(
        self,
        object_store: LocalObjectStore,
        metadata_store: SqliteMetadataStore,
        parser: Parser,
    ) -> None:
        self.object_store = object_store
        self.metadata_store = metadata_store
        self.parser = parser

    def create_job(self, request: DocumentIngestRequest) -> IngestionJob:
        job = IngestionJob(request=request)
        self.metadata_store.save_job(job)
        return job

    def ingest_bytes(
        self,
        *,
        filename: str,
        payload: bytes,
        content_type: str,
        metadata: dict[str, str] | None = None,
        tenant_id: str = "default",
        collection_id: str = "default",
    ) -> IngestionJob:
        stored_path = self.object_store.save(filename, payload)
        request = DocumentIngestRequest(
            source_path=stored_path,
            filename=filename,
            content_type=content_type,
            tenant_id=tenant_id,
            collection_id=collection_id,
            metadata=metadata or {},
        )
        job = self.create_job(request)
        return self.process_job(job.job_id)

    def process_job(self, job_id: str) -> IngestionJob:
        job = self.metadata_store.get_job(job_id)
        if job is None:
            raise KeyError(f"Unknown job: {job_id}")
        job = self.metadata_store.update_job_status(job, JobStatus.PARSING)
        try:
            parsed = self.parser.parse(job.request)
            self.metadata_store.upsert_document(job.request.tenant_id, job.request.collection_id, parsed)
            job = self.metadata_store.update_job_status(job, JobStatus.INDEXED, document_id=parsed.document_id)
            job = self.metadata_store.update_job_status(job, JobStatus.COMPLETE, document_id=parsed.document_id)
            return job
        except Exception as exc:
            return self.metadata_store.update_job_status(job, JobStatus.FAILED, error=str(exc))

    def get_job(self, job_id: str) -> IngestionJob | None:
        return self.metadata_store.get_job(job_id)
