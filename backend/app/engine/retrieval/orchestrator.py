from typing import List
from app.storage.vector_db import get_qdrant_client
from app.models.api_models import ContextChunk
from app.engine.memory.session_cache import EphemeralSessionCache
from app.core.config import config
import logging

try:
    import tiktoken
    tokenizer = tiktoken.get_encoding("cl100k_base")
    HAS_TIKTOKEN = True
except ImportError:
    HAS_TIKTOKEN = False

logger = logging.getLogger(__name__)

def count_tokens(text: str) -> int:
    """Estimates tokens. Uses tiktoken if installed, else falls back to heuristic."""
    if HAS_TIKTOKEN:
        return len(tokenizer.encode(text))
    return len(text) // 4

class RetrievalOrchestrator:
    def __init__(self, agent_id: str, session_id: str):
        self.agent_id = agent_id
        self.session_id = session_id
        self.cache = EphemeralSessionCache(session_id, agent_id)

    def retrieve(self, query: str, top_k: int = 5, max_tokens: int = 4000) -> tuple[List[ContextChunk], int, bool]:
        """
        Orchestrates the retrieval process:
        1. Query cache
        2. If miss, Query Qdrant
        3. Enforce token budget
        """
        # 1. Ephemeral Memory Check
        cached = self.cache.get_cached_context(query)
        if cached:
            logger.info(f"Cache hit for session {self.session_id} on query '{query}'")
            chunks = [ContextChunk(**c) for c in cached['chunks']]
            return chunks, cached['tokens_used'], True

        # 2. Vector DB Query
        from app.engine.ingestion.embedder import get_corporate_embeddings
        from app.storage.vector_db import get_qdrant_client
        
        # Embed the incoming query (returns a list of list, we take the first)
        query_vector = get_corporate_embeddings([query])[0]
        
        client = get_qdrant_client()
        search_result = client.query_points(
            collection_name="rag_text",
            query=query_vector,
            limit=top_k
        )
        
        raw_results = []
        for scored_point in search_result.points:
            # Safely extract payload which was set during ingestion
            payload = scored_point.payload or {}
            chunk_text = payload.get("text", "")
            doc_id = payload.get("job_id", "unknown_doc")
            
            raw_results.append(
                ContextChunk(
                    chunk_id=str(scored_point.id),
                    document_id=doc_id,
                    text=chunk_text,
                    score=scored_point.score
                )
            )

        # 3. Token Budgeting (Truncate low-score evidence if it exceeds bounds)
        final_chunks = []
        accumulated_tokens = 0

        for chunk in raw_results:
            tokens = count_tokens(chunk.text)
            if accumulated_tokens + tokens <= max_tokens:
                final_chunks.append(chunk)
                accumulated_tokens += tokens
            else:
                logger.warning(f"Dropping chunk {chunk.chunk_id} to enforce {max_tokens} token limit.")
                # We could partially truncate `chunk.text` here instead of full drop, but dropping is safer for context bounds
                break

        # 4. Save to Sliding Window Memory
        self.cache.save_context(query, {
            "chunks": [c.model_dump() for c in final_chunks],
            "tokens_used": accumulated_tokens
        })

        return final_chunks, accumulated_tokens, False
