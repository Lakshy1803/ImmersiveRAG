"""
LangGraph 2-node workflow: retrieve → generate.

State flows through:
  1. retrieve: Embeds query, searches Qdrant, populates context_chunks
  2. generate: Builds a token-budgeted prompt and calls ChatOpenAI

Designed for low token consumption (~5K per call).
"""
import logging
from typing import TypedDict, List, Optional

from langgraph.graph import StateGraph, END

from app.models.api_models import ContextChunk
from app.engine.retrieval.orchestrator import RetrievalOrchestrator
from app.engine.agents.conversation_memory import ConversationMemory
from app.core.config import config

logger = logging.getLogger(__name__)


# ── LangGraph State ────────────────────────────────────────────────────
class AgentState(TypedDict):
    question: str
    agent_id: str
    session_id: str
    system_prompt: str
    context_chunks: List[dict]
    history_context: str
    answer: str
    tokens_used: int
    cache_hit: bool


# ── Node 1: Retrieve ───────────────────────────────────────────────────
def retrieve_node(state: AgentState) -> dict:
    """Embeds the query and searches Qdrant via the existing orchestrator."""
    orchestrator = RetrievalOrchestrator(
        agent_id=state["agent_id"],
        session_id=state["session_id"]
    )

    chunks, tokens_used, cache_hit = orchestrator.retrieve(
        query=state["question"],
        top_k=5,
        max_tokens=config.max_context_tokens
    )

    return {
        "context_chunks": [c.model_dump() for c in chunks],
        "tokens_used": tokens_used,
        "cache_hit": cache_hit,
    }


# ── Node 2: Generate ──────────────────────────────────────────────────
def generate_node(state: AgentState) -> dict:
    """Builds a minimal prompt and calls the official OpenAI client."""
    from app.engine.agents.llm_client import get_llm_client
    client = get_llm_client()

    # Build context string from chunks
    chunks = state.get("context_chunks", [])
    if chunks:
        context_parts = []
        for i, chunk in enumerate(chunks):
            text = chunk.get("text", "")
            score = chunk.get("score", 0)
            context_parts.append(f"[Chunk {i+1} | {score:.0%} match]\n{text}")
        context_str = "\n\n".join(context_parts)
    else:
        context_str = "No relevant documents found in the knowledge base."

    # Build the official OpenAI message format
    messages = [
        {"role": "system", "content": state["system_prompt"]},
    ]

    # Add history context if present
    history = state.get("history_context", "")
    if history:
        messages.append({"role": "system", "content": f"Conversation history:\n{history}"})

    # User question with context
    user_content = (
        f"Context from knowledge base:\n{context_str}\n\n"
        f"User question: {state['question']}"
    )
    messages.append({"role": "user", "content": user_content})

    try:
        response = client.chat.completions.create(
            model=config.llm_model,
            messages=messages,
            max_tokens=config.llm_max_answer_tokens,
            temperature=0.3
        )
        if not response.choices:
            logger.warning(f"LLM returned no choices: {response}")
            answer = "I received an empty response from the LLM (no choices). This might be due to safety filters or a proxy issue."
        else:
            content = response.choices[0].message.content
            answer = content.strip() if content else "I received an empty content block from the LLM. Please check your model's safety settings."
    except Exception as e:
        logger.error(f"Official LLM generation failed: {e}")
        answer = f"I encountered an error generating a response: {str(e)}"

    return {"answer": answer}


# ── Graph Builder ──────────────────────────────────────────────────────
def _build_graph() -> StateGraph:
    """Constructs the 2-node LangGraph StateGraph (Sync)."""
    graph = StateGraph(AgentState)

    graph.add_node("retrieve", retrieve_node)
    graph.add_node("generate", generate_node)

    graph.set_entry_point("retrieve")
    graph.add_edge("retrieve", "generate")
    graph.add_edge("generate", END)

    return graph.compile()


# Compiled graph singleton
_compiled_graph = None


def _get_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = _build_graph()
    return _compiled_graph


# ── Public API ─────────────────────────────────────────────────────────
def run_agent_graph(
    question: str,
    agent_id: str,
    session_id: str,
    system_prompt: str,
) -> dict:
    """
    Runs the full RAG + LLM pipeline (Sync).

    Returns:
        {
            "answer": str,
            "context_chunks": List[dict],
            "tokens_used": int,
            "cache_hit": bool
        }
    """
    # Build conversation history context
    memory = ConversationMemory(session_id, agent_id)
    history_context = memory.build_history_context()

    # Run the graph using invoke()
    graph = _get_graph()
    initial_state: AgentState = {
        "question": question,
        "agent_id": agent_id,
        "session_id": session_id,
        "system_prompt": system_prompt,
        "context_chunks": [],
        "history_context": history_context,
        "answer": "",
        "tokens_used": 0,
        "cache_hit": False,
    }

    # Synchronous execution
    result = graph.invoke(initial_state)

    # Persist conversation turns
    memory.append_turn("user", question)
    memory.append_turn("assistant", result["answer"])

    # Maybe refresh the rolling summary (every 4th turn)
    memory.maybe_refresh_summary()

    return {
        "answer": result["answer"],
        "context_chunks": result["context_chunks"],
        "tokens_used": result["tokens_used"],
        "cache_hit": result["cache_hit"],
    }
