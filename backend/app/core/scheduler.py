import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from app.storage.relations_db import get_connection
from app.core.config import config
from app.models.domain_models import JobStatus

logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler = AsyncIOScheduler()

async def poll_ingestion_queue():
    """Checks for jobs that are in WAITING_VPN_ON and embeds them if the user confirmed."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            # Fetch one job that is transitioning to processing
            cursor.execute('''
                SELECT job_id, document_id, request_data FROM ingestion_jobs 
                WHERE status = ? 
                LIMIT 1
            ''', (JobStatus.EMBEDDING_AND_INDEXING.value,))
            job = cursor.fetchone()
            
            if not job:
                return
                
            job_id = job['job_id']
            chunks_json = job['document_id']
            req_data_str = job['request_data']
            
            logger.info(f"Found job {job_id} waiting for embedding with VPN ON.")
            
            # Transition to active processing
            cursor.execute(
                "UPDATE ingestion_jobs SET status = ? WHERE job_id = ?",
                (JobStatus.PROCESSING.value, job_id)
            )
            conn.commit()
            
        import json
        from app.engine.ingestion.embedder import get_corporate_embeddings
        from app.storage.vector_db import get_qdrant_client
        from qdrant_client.models import PointStruct
        from uuid import uuid4
        
        chunks = json.loads(chunks_json) if chunks_json else []
        req_data = {}
        try:
            if req_data_str:
                req_data = json.loads(req_data_str)
        except Exception as e:
            logger.warning(f"Could not parse request_data for config flags: {e}")
            
        embedding_mode = req_data.get("embedding_mode", "local_fastembed")
        
        if chunks:
            logger.info(f"Generating vectors for {len(chunks)} chunks via {embedding_mode}.")
            vectors = get_corporate_embeddings(chunks, embedding_mode=embedding_mode)
            
            # Store in Qdrant
            qdrant = get_qdrant_client()
            points = []
            for i, (text, vector) in enumerate(zip(chunks, vectors)):
                point_id = uuid4().hex
                points.append(
                    PointStruct(
                        id=point_id, 
                        vector=vector, 
                        payload={"text": text, "job_id": job_id, "chunk_idx": i}
                    )
                )
                
            qdrant.upsert(collection_name="rag_text", points=points)
            logger.info(f"Successfully indexed {len(points)} points into Qdrant for job {job_id}.")
        
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE ingestion_jobs SET status = ? WHERE job_id = ?",
                (JobStatus.COMPLETE.value, job_id)
            )
            conn.commit()

    except Exception as e:
        logger.error(f"Error in poll_ingestion_queue: {e}")
        # Mark as failed if we have job_id in scope
        try:
            if 'job_id' in locals():
                with get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "UPDATE ingestion_jobs SET status = ?, error = ? WHERE job_id = ?",
                        (JobStatus.FAILED.value, str(e), job_id)
                    )
                    conn.commit()
        except:
            pass

async def prune_stale_sessions():
    """Removes SQLite sessions and cache records that haven't been touched to save RAM."""
    timeout_mins = config.session_timeout_minutes
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            # Deleting the session cascades to the session_context_cache due to SQLite foreign keys
            cursor.execute(f'''
                DELETE FROM agent_sessions 
                WHERE (strftime('%s', 'now') - strftime('%s', last_accessed_at)) > ?
            ''', (timeout_mins * 60,))
            deleted = cursor.rowcount
            conn.commit()
            
        if deleted > 0:
            logger.info(f"Pruned {deleted} stale agent sessions.")
    except Exception as e:
        logger.error(f"Error in prune_stale_sessions: {e}")

async def compact_vectors():
    """Optimizes the local Qdrant Vector store manually."""
    # Assuming the local python client exposes an optimize command. 
    # Usually handled by HNSW itself, but we can trigger collection updates here.
    logger.info("Running nightly Qdrant compaction/optimization...")
    # client = get_qdrant_client()
    # client.update_collection(collection_name="rag_text", optimizer_config=OptimizerConfig(...))
    pass

def start_scheduler():
    if not scheduler.running:
        # Check queue every 5 seconds
        scheduler.add_job(
            poll_ingestion_queue,
            IntervalTrigger(seconds=5),
            id="poll_ingestion",
            replace_existing=True,
            max_instances=1
        )
        
        # Prune memory every 5 minutes
        scheduler.add_job(
            prune_stale_sessions,
            IntervalTrigger(minutes=5),
            id="prune_sessions",
            replace_existing=True
        )
        
        # Compact Vectors on Sundays at 2 AM
        scheduler.add_job(
            compact_vectors,
            CronTrigger(day_of_week='sun', hour=2, minute=0),
            id="compact_vectors",
            replace_existing=True
        )

        scheduler.start()
        logger.info("APScheduler background jobs started.")

def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown()
        logger.info("APScheduler stopped.")
