from typing import TypedDict, List, Dict, Any

class AgentState(TypedDict):
    agent_id: str
    session_id: str
    user_query: str
    uploaded_docs: List[Any]
    document_chunks: List[dict]
    retrieved_docs: List[dict]
    analysis_result: str
    final_report: str
    tool_outputs: Dict[str, Any]
    
    # Workflow routing state
    workflow_agents: List[str]
    current_step_index: int
    status: str
