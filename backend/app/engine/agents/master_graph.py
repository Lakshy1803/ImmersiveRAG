import logging
from typing import Literal
from langgraph.graph import StateGraph, END

from app.engine.agents.state import AgentState
from app.engine.agents.subgraphs.retrieval_agent import retrieval_subgraph
from app.engine.agents.subgraphs.document_agent import document_subgraph
from app.engine.agents.subgraphs.analysis_agent import analysis_subgraph
from app.engine.agents.subgraphs.report_agent import report_subgraph

logger = logging.getLogger(__name__)

# Map friendly agent names from workflow config to actual graph nodes
AGENT_NODE_MAP = {
    "document_agent": "document",
    "retrieval_agent": "retrieval",
    "analysis_agent": "analysis",
    "report_agent": "report"
}

def router_node(state: AgentState) -> dict:
    """The master router checks the workflow list to see what's next."""
    logger.info(f"Master Router executing step index {state.get('current_step_index', 0)}")
    return {} # Doesn't mutate state, just pass-through to evaluate conditions

def routing_logic(state: AgentState) -> str:
    """Conditional edge logic that determines the next node to execute."""
    workflow = state.get("workflow_agents", [])
    current_idx = state.get("current_step_index", 0)
    
    if current_idx >= len(workflow):
        logger.info("Workflow complete. Routing to END.")
        return END
        
    next_agent = workflow[current_idx]
    if next_agent in AGENT_NODE_MAP:
        logger.info(f"Routing to -> {next_agent}")
        return AGENT_NODE_MAP[next_agent]
    
    # Fallback / Error
    logger.error(f"Unknown agent in workflow config: {next_agent}. Terminating.")
    return END

def build_master_graph() -> StateGraph:
    """Constructs the Master Orchestrator state graph."""
    graph = StateGraph(AgentState)
    
    # 1. Add Master Router Node
    graph.add_node("router", router_node)
    
    # 2. Add Subgraph Hub Nodes
    graph.add_node("document", document_subgraph)
    graph.add_node("retrieval", retrieval_subgraph)
    graph.add_node("analysis", analysis_subgraph)
    graph.add_node("report", report_subgraph)
    
    # 3. Flow begins at the Orchestrator Router
    graph.set_entry_point("router")
    
    # 4. Router distributes to respective edges conditionally
    graph.add_conditional_edges(
        "router", 
        routing_logic
    )
    
    # 5. Subgraphs always return to Router once their specific stage is complete
    graph.add_edge("document", "router")
    graph.add_edge("retrieval", "router")
    graph.add_edge("analysis", "router")
    graph.add_edge("report", "router")
    
    return graph.compile()
    
# Exportable singleton
master_orchestrator = build_master_graph()
