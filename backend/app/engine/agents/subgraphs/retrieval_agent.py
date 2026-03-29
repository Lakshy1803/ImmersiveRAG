import logging
from langgraph.graph import StateGraph, END
from app.engine.agents.state import AgentState
from app.engine.retrieval.orchestrator import RetrievalOrchestrator
from app.core.config import config

logger = logging.getLogger(__name__)

def build_query_node(state: AgentState) -> dict:
    """Extracts or rewrites the query for optimal retrieval."""
    logger.info("Executing Retrieval Agent Subgraph: build_query_node")
    query = state.get("user_query", "")
    # In Phase 1, we just use the raw query. 
    # LLM-based query rewriting against chat memory can be easily added here.
    return {"user_query": query}

def vector_search_node(state: AgentState) -> dict:
    """Executes semantic search against the Qdrant vector database."""
    logger.info("Executing Retrieval Agent Subgraph: vector_search_node")
    query = state.get("user_query", "")
    
    # Instantiate Existing Orchestrator to search Qdrant via FastEmbed
    orchestrator = RetrievalOrchestrator(
        agent_id=state.get("agent_id", "default_agent"),
        session_id=state.get("session_id", "default_session")
    )
    
    chunks, tokens_used, cache_hit = orchestrator.retrieve(
        query=query,
        top_k=5,
        max_tokens=config.max_context_tokens
    )
    
    return {"retrieved_docs": [c.model_dump() for c in chunks]}

def rerank_results_node(state: AgentState) -> dict:
    """Filters low-confidence matches and finalizes the result set."""
    logger.info("Executing Retrieval Agent Subgraph: rerank_results_node")
    raw_docs = state.get("retrieved_docs", [])
    
    # Filter and sort by score descending
    # Retain matches strictly above 30% confidence loosely in Phase 1
    filtered_docs = [doc for doc in raw_docs if doc.get("score", 0) > 0.30]
    filtered_docs.sort(key=lambda x: x.get("score", 0), reverse=True)
    
    # Final node of the subgraph MUST increment the Master Orchestrator's step index!
    next_step = state.get("current_step_index", 0) + 1
    
    return {
        "retrieved_docs": filtered_docs,
        "current_step_index": next_step
    }

def build_retrieval_subgraph() -> StateGraph:
    """Builds the 3-node LangGraph subgraph for Retrieval."""
    graph = StateGraph(AgentState)
    
    graph.add_node("build_query", build_query_node)
    graph.add_node("vector_search", vector_search_node)
    graph.add_node("rerank_results", rerank_results_node)
    
    graph.set_entry_point("build_query")
    graph.add_edge("build_query", "vector_search")
    graph.add_edge("vector_search", "rerank_results")
    graph.add_edge("rerank_results", END)
    
    return graph.compile()

# Exportable Singleton Subgraph
retrieval_subgraph = build_retrieval_subgraph()
