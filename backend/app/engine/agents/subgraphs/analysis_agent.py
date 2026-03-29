import logging
from langgraph.graph import StateGraph, END
from app.engine.agents.state import AgentState
from app.engine.agents.llm_client import get_llm_client
from app.core.config import config

logger = logging.getLogger(__name__)

def construct_prompt_node(state: AgentState) -> dict:
    """Combines retrieved documents and the user query into an LLM instruction prompt."""
    logger.info("Executing Analysis Agent Subgraph: construct_prompt_node")
    docs = state.get("retrieved_docs", [])
    query = state.get("user_query", "")
    
    if not docs:
        context_str = "No relevant documents found in the database. Please answer based solely on your internal knowledge."
    else:
        # Convert Qdrant chunk dicts to text passages
        context_texts = []
        for d in docs:
            if isinstance(d, dict) and "text" in d:
                context_texts.append(d["text"])
            else:
                context_texts.append(str(d))
        
        context_str = "\n\n---\n\n".join(context_texts)
        
    prompt = f"""You are an expert analytical reasoning engine. 
Based on the following extracted context passages, please provide a comprehensive and accurate analysis answering the user's query. 
Use markdown formatting where appropriate for code, lists, and emphasis. IF the context is insufficient, state that clearly but try to reason as best you can.

CONTEXT:
{context_str}

USER QUERY:
{query}

ANALYSIS:
"""
    # Temporarily store the prompt directly in analysis_result to pass it to the next node
    return {"analysis_result": prompt}

def run_llm_node(state: AgentState) -> dict:
    """Executes a synchronous call to the LLM (OpenAI / Groq) using the cached configuration."""
    logger.info("Executing Analysis Agent Subgraph: run_llm_node")
    prompt = state.get("analysis_result", "")
    
    if not prompt:
        return {"analysis_result": "Error: No prompt available for LLM analysis."}
        
    try:
        client = get_llm_client()
        response = client.chat.completions.create(
            model=config.llm_model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=config.llm_max_answer_tokens,
            temperature=0.3
        )
        answer = response.choices[0].message.content
        return {"analysis_result": answer}
    except Exception as e:
        logger.error(f"Analysis Agent LLM generation failed: {e}")
        return {"analysis_result": f"Analysis failed due to LLM error: {e}"}

def generate_analysis_node(state: AgentState) -> dict:
    """Finalizes reasoning output and steps the master graph counter."""
    logger.info("Executing Analysis Agent Subgraph: generate_analysis_node")
    next_step = state.get("current_step_index", 0) + 1
    return {"current_step_index": next_step}

def build_analysis_subgraph() -> StateGraph:
    """Builds the reasoning and generation layer subgraph."""
    graph = StateGraph(AgentState)
    
    graph.add_node("construct_prompt", construct_prompt_node)
    graph.add_node("run_llm", run_llm_node)
    graph.add_node("generate_analysis", generate_analysis_node)
    
    graph.set_entry_point("construct_prompt")
    graph.add_edge("construct_prompt", "run_llm")
    graph.add_edge("run_llm", "generate_analysis")
    graph.add_edge("generate_analysis", END)
    
    return graph.compile()

# Provide Singleton export
analysis_subgraph = build_analysis_subgraph()
