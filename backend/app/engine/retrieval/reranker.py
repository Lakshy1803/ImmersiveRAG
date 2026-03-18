"""
Cross-encoder re-ranker for ImmersiveRAG.

After Qdrant returns top-20 candidates by cosine similarity, this module
scores each (query, chunk) pair with a cross-encoder and returns the
top_n highest-scoring chunks.

Model: cross-encoder/ms-marco-MiniLM-L-6-v2  (~80 MB, all local, no API key)
"""
import logging
from typing import List

from app.models.api_models import ContextChunk

logger = logging.getLogger(__name__)

_reranker = None


def _get_reranker():
    """Lazy-load the cross-encoder model (downloads ~80 MB on first use)."""
    global _reranker
    if _reranker is None:
        try:
            from sentence_transformers import CrossEncoder
            _reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2", max_length=512)
            logger.info("Cross-encoder re-ranker loaded.")
        except Exception as e:
            logger.warning(f"Could not load cross-encoder: {e}. Re-ranking disabled.")
            _reranker = "disabled"
    return _reranker


def rerank(query: str, chunks: List[ContextChunk], top_n: int = 5) -> List[ContextChunk]:
    """
    Re-ranks the given chunks against the query using the cross-encoder.

    Args:
        query: Original user query
        chunks: Candidate chunks retrieved from Qdrant (typically top-20)
        top_n: Number of best chunks to return after re-ranking

    Returns:
        The top_n most relevant chunks, sorted by cross-encoder score descending.
    """
    if not chunks:
        return chunks

    reranker = _get_reranker()
    if reranker == "disabled":
        # Graceful fallback: return original ordering
        return chunks[:top_n]

    try:
        pairs = [(query, chunk.text) for chunk in chunks]
        scores = reranker.predict(pairs)

        # Pair each chunk with its score and sort descending
        scored = sorted(zip(scores, chunks), key=lambda x: x[0], reverse=True)
        reranked = [chunk for _, chunk in scored[:top_n]]

        logger.info(
            f"Re-ranked {len(chunks)} → {len(reranked)} chunks. "
            f"Top score: {scored[0][0]:.3f}, bottom: {scored[top_n-1][0]:.3f}"
        )
        return reranked

    except Exception as e:
        logger.warning(f"Re-ranking failed, using original order: {e}")
        return chunks[:top_n]
