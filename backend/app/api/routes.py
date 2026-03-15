from __future__ import annotations

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile

from app.core.config import settings
from app.models import QueryRequest
from app.services.container import ServiceContainer, app_lifespan, get_container


def container_dep() -> ServiceContainer:
    return get_container()


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, lifespan=app_lifespan)

    @app.get("/health")
    def health(container: ServiceContainer = Depends(container_dep)) -> dict:
        report = container.diagnostics.report()
        return report.model_dump()

    @app.get("/health/ready")
    def ready(container: ServiceContainer = Depends(container_dep)) -> dict[str, str]:
        report = container.diagnostics.report()
        if report.status != "ok":
            raise HTTPException(status_code=503, detail=report.model_dump())
        return {"status": "ready"}

    @app.post("/ingest")
    async def ingest_document(
        file: UploadFile = File(...),
        tenant_id: str = Form("default"),
        collection_id: str = Form("default"),
        container: ServiceContainer = Depends(container_dep),
    ) -> dict:
        payload = await file.read()
        if len(payload) > settings.max_file_size_bytes:
            raise HTTPException(status_code=413, detail="File exceeds configured size limit.")
        if file.content_type not in {"application/pdf", "image/png", "image/jpeg", "image/jpg"}:
            raise HTTPException(status_code=415, detail="Unsupported file type.")

        job = container.ingestion.ingest_bytes(
            filename=file.filename or "upload.bin",
            payload=payload,
            content_type=file.content_type,
            tenant_id=tenant_id,
            collection_id=collection_id,
        )
        if job.status.value == "failed":
            raise HTTPException(status_code=400, detail=job.error or "Ingestion failed.")
        container.retrieval.index_document(job.document_id or "")
        refreshed_job = container.ingestion.get_job(job.job_id)
        return {"job": refreshed_job.model_dump() if refreshed_job else job.model_dump()}

    @app.get("/jobs/{job_id}")
    def get_job(job_id: str, container: ServiceContainer = Depends(container_dep)) -> dict:
        job = container.ingestion.get_job(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Job not found.")
        return {"job": job.model_dump()}

    @app.post("/index/{document_id}")
    def index_document(document_id: str, container: ServiceContainer = Depends(container_dep)) -> dict:
        try:
            document = container.retrieval.index_document(document_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return {"document": document.model_dump()}

    @app.post("/query")
    def query_documents(query: QueryRequest, container: ServiceContainer = Depends(container_dep)) -> dict:
        return {"response": container.answering.answer(query).model_dump()}

    return app
