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
    model_settings: dict


# ── Node 1: Retrieve ───────────────────────────────────────────────────
def retrieve_node(state: AgentState) -> dict:
    """Embeds the query and searches Qdrant via the existing orchestrator."""
    orchestrator = RetrievalOrchestrator(
        agent_id=state["agent_id"],
        session_id=state["session_id"]
    )

    settings = state.get("model_settings", {})
    top_k = int(settings.get("top_k", 5))
    max_context = int(settings.get("max_context_tokens", config.max_context_tokens))

    chunks, tokens_used, cache_hit = orchestrator.retrieve(
        query=state["question"],
        top_k=top_k,
        max_tokens=max_context
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
            metadata = chunk.get("metadata", {})
            file_name = metadata.get("file_name", f"Chunk {i+1}")
            page = metadata.get("page_label", "N/A")
            heading = metadata.get("heading", "Unknown")
            context_parts.append(f"[Source: {file_name} | Page: {page} | Heading: {heading} | {score:.0%} match]\n{text}")
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

    # Extract overrides from model_settings if provided
    settings = state.get("model_settings", {})
    gen_model = config.llm_model  # Model name override could go here too if needed later
    max_tokens = int(settings.get("max_tokens", config.llm_max_answer_tokens))
    temperature = float(settings.get("temperature", 0.3))

    try:
        response = client.chat.completions.create(
            model=gen_model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature
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


# ── Node 3: Logger (Observability) ─────────────────────────────────────
def logger_node(state: AgentState) -> dict:
    """
    Observability node: Logs the execution state, tokens used, and tool calls.
    Satisfies the requirement for a 'logger' node in the multi-agent graph.
    """
    logger.info("===" * 10)
    logger.info(f"[GRAPH LOGGER] Session: {state.get('session_id')}")
    logger.info(f"[GRAPH LOGGER] Agent: {state.get('agent_id')}")
    logger.info(f"[GRAPH LOGGER] Tokens Used in Retrieval: {state.get('tokens_used')}")
    logger.info(f"[GRAPH LOGGER] Cache Hit: {state.get('cache_hit')}")
    
    ans_length = len(state.get('answer', ''))
    logger.info(f"[GRAPH LOGGER] Generated Answer Length: {ans_length} chars")
    
    context_len = len(state.get('context_chunks', []))
    logger.info(f"[GRAPH LOGGER] Context Chunks Provided: {context_len}")
    logger.info("===" * 10)
    
    # The logger node doesn't mutate the state, just observes it.
    return dict()

# ── Graph Builder ──────────────────────────────────────────────────────
def _build_graph() -> StateGraph:
    """Constructs the 3-node LangGraph StateGraph (Sync)."""
    graph = StateGraph(AgentState)

    graph.add_node("retrieve", retrieve_node)
    graph.add_node("generate", generate_node)
    graph.add_node("logger", logger_node)

    graph.set_entry_point("retrieve")
    graph.add_edge("retrieve", "generate")
    graph.add_edge("generate", "logger")
    graph.add_edge("logger", END)

    return graph.compile()


# Compiled graph singleton
_compiled_graph = None


def _get_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = _build_graph()
    return _compiled_graph


# ── Streaming Public API ───────────────────────────────────────────────
def stream_agent_graph(
    question: str,
    agent_id: str,
    session_id: str,
    system_prompt: str,
    model_settings: dict = None,
):
    """
    Streaming variant of run_agent_graph.

    Yields SSE-formatted strings:
      - data: {"type": "chunk", "text": "..."}\n\n   — one token at a time
      - data: {"type": "context", "chunks": [...], "cache_hit": bool, "tokens_used": int}\n\n
      - data: {"type": "done"}\n\n

    The retrieve node runs synchronously first (fast), then the generate node
    streams tokens directly from the OpenAI client.
    """
    import json
    from app.engine.agents.llm_client import get_llm_client

    # ── Step 1: Retrieve (blocking, fast) ─────────────────────────────
    memory = ConversationMemory(session_id, agent_id)
    history_context = memory.build_history_context()

    orchestrator = RetrievalOrchestrator(
        agent_id=agent_id,
        session_id=session_id
    )
    
    settings = model_settings or {}
    top_k = int(settings.get("top_k", 5))
    max_context = int(settings.get("max_context_tokens", config.max_context_tokens))

    chunks, tokens_used, cache_hit = orchestrator.retrieve(
        query=question,
        top_k=top_k,
        max_tokens=max_context
    )
    context_chunks = [c.model_dump() for c in chunks]

    # Send context metadata first so the frontend can show sources immediately
    yield f"data: {json.dumps({'type': 'context', 'chunks': context_chunks, 'cache_hit': cache_hit, 'tokens_used': tokens_used})}\n\n"

    # ── Step 2: Build prompt ───────────────────────────────────────────
    if context_chunks:
        context_parts = []
        for i, chunk in enumerate(context_chunks):
            text = chunk.get("text", "")
            score = chunk.get("score", 0)
            metadata = chunk.get("metadata", {})
            file_name = metadata.get("file_name", f"Chunk {i+1}")
            page = metadata.get("page_label", "N/A")
            heading = metadata.get("heading", "Unknown")
            context_parts.append(f"[Source: {file_name} | Page: {page} | Heading: {heading} | {score:.0%} match]\n{text}")
        context_str = "\n\n".join(context_parts)
    else:
        context_str = "No relevant documents found in the knowledge base."

    messages = [{"role": "system", "content": system_prompt}]
    if history_context:
        messages.append({"role": "system", "content": f"Conversation history:\n{history_context}"})
    messages.append({"role": "user", "content": f"Context from knowledge base:\n{context_str}\n\nUser question: {question}"})

    settings = model_settings or {}
    max_tokens = int(settings.get("max_tokens", config.llm_max_answer_tokens))
    temperature = float(settings.get("temperature", 0.3))

    # ── Step 3: Stream tokens ──────────────────────────────────────────
    full_answer = ""
    try:
        client = get_llm_client()
        stream = client.chat.completions.create(
            model=config.llm_model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            stream=True,  # ← the one flag that enables streaming
        )
        for chunk in stream:
            delta = chunk.choices[0].delta.content if chunk.choices else None
            if delta:
                full_answer += delta
                yield f"data: {json.dumps({'type': 'chunk', 'text': delta})}\n\n"
    except Exception as e:
        logger.error(f"Streaming LLM generation failed: {e}")
        error_text = f"⚠️ Error: {str(e)}"
        full_answer = error_text
        yield f"data: {json.dumps({'type': 'chunk', 'text': error_text})}\n\n"

    # ── Step 4: Persist memory ─────────────────────────────────────────
    memory.append_turn("user", question)
    memory.append_turn("assistant", full_answer)
    memory.maybe_refresh_summary()

    yield f"data: {json.dumps({'type': 'done'})}\n\n"


# ── Blocking Public API ────────────────────────────────────────────────
def run_agent_graph(
    question: str,
    agent_id: str,
    session_id: str,
    system_prompt: str,
    model_settings: dict = None,
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
        "model_settings": model_settings or {},
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
