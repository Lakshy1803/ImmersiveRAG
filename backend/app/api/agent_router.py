from fastapi import APIRouter, Depends, HTTPException, status
from app.models.api_models import AgentQueryRequest, AgentContextResponse, ContextChunk
from app.api.dependencies import get_config
from app.core.config import AppConfig

router = APIRouter(prefix="/agent", tags=["Shared Context Agent Services"])

@router.post("/query", response_model=AgentContextResponse)
async def query_context(request: AgentQueryRequest, config: AppConfig = Depends(get_config)):
    """
    Entrypoint for LangGraph agents.
    It returns chunks within a hard token limit instead of generating an LLM answer.
    """
    # 1. Initialize the orchestrator for this specific agent and session
    from app.engine.retrieval.orchestrator import RetrievalOrchestrator
    
    orchestrator = RetrievalOrchestrator(
        agent_id=request.agent_id,
        session_id=request.session_id
    )
    
    # 2. Retrieve chunks (from cache or Qdrant) within the token bounds
    chunks, tokens_used, cache_hit = orchestrator.retrieve(
        query=request.question,
        top_k=request.top_k,
        max_tokens=request.max_tokens
    )
    
    # 3. Return structured context to the LangGraph agent
    return AgentContextResponse(
        agent_id=request.agent_id,
        session_id=request.session_id,
        question=request.question,
        cache_hit=cache_hit,
        total_tokens_used=tokens_used,
        extracted_context=chunks
    )
