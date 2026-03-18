import json
from app.models.domain_models import JobStatus, DocumentIngestRequest, IngestionJob
from app.storage.relations_db import get_connection
from app.engine.ingestion.parser import run_llamaparse_extraction
from app.engine.ingestion.chunker import chunk_markdown_content

class IngestionPipelineManager:
    """
    Manages the state transitions for the VPN-aware ingestion pipeline.
    """
    
    def __init__(self):
        # We rely on context managers or direct connections for state transitions outside the request path
        pass

    def create_job(self, request: DocumentIngestRequest) -> IngestionJob:
        """
        Step 1: User calls /ingest. We create a job and mark it as PROCESSING.
        """
        job = IngestionJob(
            request=request,
            status=JobStatus.PROCESSING
        )
        
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO ingestion_jobs (job_id, status, request_data, document_id)
                VALUES (?, ?, ?, ?)
            ''', (job.job_id, job.status.value, request.model_dump_json(), job.document_id))
            conn.commit()
            
        return job

    async def execute_parsing_stage(self, job_id: str) -> None:
        """
        Step 2: Parses the document based on the extraction_mode specified in the request.
        Updates state to EMBEDDING_AND_INDEXING when done so the APScheduler picks it up.
        """
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT request_data FROM ingestion_jobs WHERE job_id = ?", (job_id,))
            row = cursor.fetchone()
            if not row:
                raise ValueError(f"Job {job_id} not found.")
                
            req_data = DocumentIngestRequest.model_validate_json(row['request_data'])

        import aiofiles
        import os

        try:
            # 1. Extraction Selection
            if req_data.extraction_mode == "cloud_llamaparse":
                markdown_content = await run_llamaparse_extraction(req_data.source_path)
            else:
                # Local fallback extraction
                if req_data.source_path.endswith('.pdf'):
                    import PyPDF2
                    text_content = []
                    with open(req_data.source_path, 'rb') as pdf_file:
                        pdf_reader = PyPDF2.PdfReader(pdf_file)
                        for page in pdf_reader.pages:
                            page_text = page.extract_text()
                            if page_text:
                                text_content.append(page_text)
                    if not text_content:
                        raise ValueError(f"PDF '{os.path.basename(req_data.source_path)}' yielded no extractable text.")
                    markdown_content = "\n\n".join(text_content)
                else:
                    async with aiofiles.open(req_data.source_path, mode='r', encoding='utf-8', errors='replace') as f:
                        markdown_content = await f.read()

            # 2. Local Chunking
            chunks = chunk_markdown_content(markdown_content)

            # 3. Save chunks into SQLite so the scheduler can embed them
            chunk_payload = json.dumps(chunks)

            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE ingestion_jobs SET status = ?, document_id = ? WHERE job_id = ?",
                    (JobStatus.EMBEDDING_AND_INDEXING.value, chunk_payload, job_id)
                )
                conn.commit()

        except Exception as e:
            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE ingestion_jobs SET status = ?, error = ? WHERE job_id = ?", 
                    (JobStatus.FAILED.value, str(e), job_id)
                )
                conn.commit()
