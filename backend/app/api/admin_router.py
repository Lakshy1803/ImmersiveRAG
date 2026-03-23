from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, BackgroundTasks
from typing import Dict, Any, Optional
from pydantic import BaseModel
import os
import shutil

from app.models.domain_models import JobStatus, DocumentIngestRequest
from app.models.api_models import IngestStatusResponse
from app.api.dependencies import get_config
from app.core.config import AppConfig
from app.engine.ingestion.pipeline import IngestionPipelineManager
from uuid import uuid4

class AdminConfigResponse(BaseModel):
    embedding_model: str
    generation_model: str
    max_context_tokens: int
    llm_max_answer_tokens: int
    sliding_window_size: int
    temperature: float = 0.3
    top_k: int = 5

class QdrantStatsResponse(BaseModel):
    collection_name: str
    vector_count: int
    status: str

router = APIRouter(prefix="/admin", tags=["Admin & Ingestion"])

@router.post("/ingest", response_model=IngestStatusResponse)
async def start_ingestion(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    tenant_id: str = Form("default"),
    collection_id: str = Form("default"),
    extraction_mode: str = Form("local_markdown"),
    embedding_mode: str = Form("local_fastembed"),
    config: AppConfig = Depends(get_config)
):
    """
    User uploads a PDF/Image for ingestion along with configuration modes.
    System saves the file and immediately begins processing locally without waiting for API triggers.
    """
    # 1. Ensure upload directory exists
    upload_dir = os.path.join(config.data_dir, "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    
    # 2. Save the incoming binary file to local disk
    safe_filename = file.filename or "unknown_upload.bin"
    file_path = os.path.join(upload_dir, f"{uuid4().hex}_{safe_filename}")
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    # 3. Create the ingest request model (including bypassing config)
    request_data = DocumentIngestRequest(
        source_path=file_path,
        filename=safe_filename,
        content_type=file.content_type or "application/octet-stream",
        tenant_id=tenant_id,
        collection_id=collection_id,
        extraction_mode=extraction_mode,
        embedding_mode=embedding_mode
    )
    
    # 4. Save job to SQLite state machine
    manager = IngestionPipelineManager()
    job = manager.create_job(request=request_data)
    
    # 5. Immediately dispatch the parsing stage in the background
    background_tasks.add_task(manager.execute_parsing_stage, job.job_id)
    
    return IngestStatusResponse(
        job_id=job.job_id,
        status=JobStatus.PROCESSING,
        message="File uploaded successfully. Processing will continue seamlessly in the background."
    )

@router.post("/ingest/bulk", response_model=Dict[str, Any])
async def start_bulk_ingestion(
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(...),
    tenant_id: str = Form("default"),
    collection_id: str = Form("default"),
    extraction_mode: str = Form("local_markdown"),
    embedding_mode: str = Form("local_fastembed"),
    config: AppConfig = Depends(get_config)
):
    """
    Bulk ingest multiple files at once. 
    Returns a dictionary of tracking objects.
    """
    upload_dir = os.path.join(config.data_dir, "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    
    manager = IngestionPipelineManager()
    jobs = []
    
    for file in files:
        safe_filename = file.filename or "unknown_upload.bin"
        file_path = os.path.join(upload_dir, f"{uuid4().hex}_{safe_filename}")
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        request_data = DocumentIngestRequest(
            source_path=file_path,
            filename=safe_filename,
            content_type=file.content_type or "application/octet-stream",
            tenant_id=tenant_id,
            collection_id=collection_id,
            extraction_mode=extraction_mode,
            embedding_mode=embedding_mode
        )
        
        job = manager.create_job(request=request_data)
        background_tasks.add_task(manager.execute_parsing_stage, job.job_id)
        
        jobs.append({
            "filename": safe_filename,
            "job_id": job.job_id,
            "status": job.status.value
        })
        
    return {
        "message": f"Successfully queued {len(jobs)} files for ingestion.",
        "jobs": jobs
    }

@router.get("/config/current", response_model=AdminConfigResponse)
async def get_current_config(config: AppConfig = Depends(get_config)):
    """Returns the current public configuration for display in Model Settings UI."""
    return AdminConfigResponse(
        embedding_model=config.embedding_model,
        generation_model=config.llm_model,
        max_context_tokens=config.max_context_tokens,
        llm_max_answer_tokens=config.llm_max_answer_tokens,
        sliding_window_size=config.sliding_window_size,
    )

@router.get("/qdrant/stats", response_model=QdrantStatsResponse)
async def get_qdrant_stats():
    """Returns basic stats about the Qdrant vector store collections."""
    from app.storage.vector_db import get_qdrant_client, COLLECTION_NAME
    
    try:
        qdrant = get_qdrant_client()
        info = qdrant.get_collection(COLLECTION_NAME)
        return QdrantStatsResponse(
            collection_name=COLLECTION_NAME,
            vector_count=info.points_count or 0,
            status="green" if info.status and info.status.value == "green" else str(info.status)
        )
    except Exception as e:
        return QdrantStatsResponse(
            collection_name=COLLECTION_NAME,
            vector_count=0,
            status=f"offline: {e}"
        )

@router.get("/ingest/{job_id}/status", response_model=IngestStatusResponse)
async def get_job_status(job_id: str):
    """
    Check the current status of an ingestion job from the SQLite state machine.
    """
    from app.storage.relations_db import get_connection
    
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT job_id, status, error FROM ingestion_jobs WHERE job_id = ?",
            (job_id,)
        )
        row = cursor.fetchone()
    
    if not row:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")
    
    status_value = row["status"]
    error_msg = row["error"]
    
    # Map status to a human-readable message
    messages = {
        "queued": "Job is queued and waiting to be picked up.",
        "processing": "Job is currently being parsed and chunked.",
        "embedding_and_indexing": "Chunks are ready — waiting for embedding scheduler.",
        "complete": "Document successfully processed and vectors embedded!",
        "failed": f"Job failed: {error_msg or 'Unknown error'}",
    }
    
    try:
        job_status = JobStatus(status_value)
    except ValueError:
        # Handle any legacy statuses (e.g. 'waiting_vpn_off') gracefully
        job_status = JobStatus.FAILED
        return IngestStatusResponse(
            job_id=job_id,
            status=job_status,
            message=f"Job has a legacy status '{status_value}' — please re-upload."
        )
    
    return IngestStatusResponse(
        job_id=job_id,
        status=job_status,
        message=messages.get(status_value, f"Status: {status_value}")
    )

@router.get("/debug/vectors")
async def view_qdrant_vectors(limit: int = 1):
    """
    DEBUG: See the actual mathematical sequences generated by fastembed!
    """
    from app.storage.vector_db import get_qdrant_client
    qdrant = get_qdrant_client()
    try:
        # Scroll returns a tuple (records, next_page_offset)
        records, _ = qdrant.scroll(
            collection_name="rag_text", 
            limit=limit, 
            with_vectors=True
        )
        
        if not records:
            return {"message": "No vectors found. Make sure you fully complete an upload and VPN ingestion flow first!"}
            
        results = []
        for record in records:
            # We crop the array to 10 numbers so we don't crash the browser rendering 384 or 1536 floats
            vec_preview = record.vector[:10] if record.vector else []
            dim_size = len(record.vector) if record.vector else 0
            
            results.append({
                "point_id": record.id,
                "payload": record.payload,
                "dimension_size": dim_size,
                "sequence_preview": vec_preview
            })
            
        return {"vectors": results}
    except Exception as e:
        return {"error": str(e)}


@router.delete("/debug/purge-vectors", summary="Wipe all vectors from Qdrant and reset job history")
async def purge_all_vectors():
    """
    DEBUG: Completely removes all Qdrant vector data (including on-disk files)
    and clears all SQLite state (jobs, sessions, caches).
    Use this for a full clean-slate reset before uploading new documents.
    """
    from app.storage.vector_db import get_qdrant_client, COLLECTION_NAME, reset_qdrant_client, init_qdrant_collections
    from app.storage.relations_db import get_connection
    from app.core.config import config

    qdrant = get_qdrant_client()
    deleted_count = 0

    try:
        info = qdrant.get_collection(COLLECTION_NAME)
        deleted_count = info.points_count or 0
    except Exception:
        pass

    # 1. Close the Qdrant client singleton — releases all file locks and internal caches
    reset_qdrant_client()

    # 2. Physically remove all on-disk Qdrant storage to guarantee zero residual data
    qdrant_dir = config.qdrant_path
    try:
        if os.path.exists(qdrant_dir):
            shutil.rmtree(qdrant_dir)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to remove Qdrant data directory: {e}")

    # 3. Reinitialize clean collections with a fresh client
    try:
        init_qdrant_collections()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reinitialize Qdrant collections: {e}")

    # 4. Wipe all SQLite state: jobs, session caches, session records, and conversation history
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM conversation_messages")
        cursor.execute("DELETE FROM session_context_cache")
        cursor.execute("DELETE FROM agent_sessions")
        cursor.execute("DELETE FROM ingestion_jobs")
        conn.commit()

    return {
        "message": f"Purged {deleted_count} vectors. Qdrant storage wiped and recreated. All caches and job history cleared.",
        "vectors_deleted": deleted_count
    }
