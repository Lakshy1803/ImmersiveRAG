from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.concurrency import run_in_threadpool
from typing import List, AsyncGenerator
from uuid import uuid4
import json
import asyncio

from app.models.api_models import (
    AgentQueryRequest, AgentContextResponse, ContextChunk,
    AgentChatRequest, AgentChatResponse,
    AgentDefinition, AgentConfigRequest,
)
from app.storage.relations_db import get_connection

router = APIRouter(prefix="/agent", tags=["Agent Services"])


# ── Legacy Retrieval-Only Endpoint (backward compat) ───────────────────
@router.post("/query", response_model=AgentContextResponse)
async def query_context(request: AgentQueryRequest):
    """
    Legacy: Returns raw context chunks without LLM generation.
    Kept for backward compatibility with older clients.
    """
    from app.engine.retrieval.orchestrator import RetrievalOrchestrator

    orchestrator = RetrievalOrchestrator(
        agent_id=request.agent_id,
        session_id=request.session_id
    )

    chunks, tokens_used, cache_hit = orchestrator.retrieve(
        query=request.question,
        top_k=request.top_k,
        max_tokens=request.max_tokens
    )

    return AgentContextResponse(
        agent_id=request.agent_id,
        session_id=request.session_id,
        question=request.question,
        cache_hit=cache_hit,
        total_tokens_used=tokens_used,
        extracted_context=chunks
    )


# ── New Multi-Agent Chat Endpoint ──────────────────────────────────────
@router.post("/chat", response_model=AgentChatResponse)
async def agent_chat(request: AgentChatRequest):
    """
    Full RAG + LLM generation pipeline via LangGraph.
    Retrieves context from Qdrant, builds a prompt with conversation history,
    and generates an answer using the company LLM.
    """
    # 1. Look up the agent definition
    agent_def = _get_agent_definition(request.agent_id)
    if not agent_def:
        raise HTTPException(status_code=404, detail=f"Agent '{request.agent_id}' not found.")

    # 2. Run the LangGraph pipeline (Async)
    from app.engine.agents.graph_runner import run_agent_graph

    result = await run_agent_graph(
        question=request.question,
        agent_id=request.agent_id,
        session_id=request.session_id,
        system_prompt=agent_def["system_prompt"],
    )

    # 3. Map raw chunk dicts back to ContextChunk models
    context_chunks = [ContextChunk(**c) for c in result.get("context_chunks", [])]

    return AgentChatResponse(
        answer=result["answer"],
        context_chunks=context_chunks,
        tokens_used=result["tokens_used"],
        cache_hit=result["cache_hit"],
    )


# ── Streaming Chat Endpoint (SSE) ────────────────────────────────────────────
@router.post("/chat/stream")
async def agent_chat_stream(request: AgentChatRequest):
    """
    Streaming variant of /agent/chat.
    Returns Server-Sent Events:
      - data: {"token": "..."} for each LLM token
      - data: {"done": true, "context_chunks": [...], "cache_hit": bool} at the end
    """
    agent_def = _get_agent_definition(request.agent_id)
    if not agent_def:
        raise HTTPException(status_code=404, detail=f"Agent '{request.agent_id}' not found.")

    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            # Padding to force proxy flush (1KB)
            yield ":" + " " * 1024 + "\n\n"
            yield f"data: {json.dumps({'token': '[CONNECTED] '})}\n\n"
            from app.engine.agents.conversation_memory import ConversationMemory
            from app.engine.retrieval.orchestrator import RetrievalOrchestrator
            # Step 1: Retrieve context
            orchestrator = RetrievalOrchestrator(
                agent_id=request.agent_id,
                session_id=request.session_id
            )
            from app.core.config import config as app_config
            chunks, tokens_used, cache_hit = await run_in_threadpool(
                orchestrator.retrieve,
                query=request.question,
                top_k=5,
                max_tokens=app_config.max_context_tokens
            )

            # Step 2: Build prompt messages
            memory = ConversationMemory(request.session_id, request.agent_id)
            history_context = memory.build_history_context()

            context_str = "No relevant documents found in the knowledge base."
            if chunks:
                context_str = "\n\n".join(
                    f"[Chunk {i+1} | {c.score:.0%} match]\n{c.text}"
                    for i, c in enumerate(chunks)
                )

            # System and User messages (OpenAI dictionary format)
            messages = [{"role": "system", "content": agent_def["system_prompt"]}]
            if history_context:
                messages.append({"role": "system", "content": f"Conversation history:\n{history_context}"})
            
            messages.append({"role": "user", "content": f"Context from knowledge base:\n{context_str}\n\nUser question: {request.question}"})

            # Step 3: Stream tokens from AsyncOpenAI
            from app.engine.agents.llm_client import get_llm_client
            client = get_llm_client()
            full_answer = ""

            response = await client.chat.completions.create(
                model=app_config.llm_model,
                messages=messages,
                stream=True,
                max_tokens=app_config.llm_max_answer_tokens,
                temperature=0.3
            )

            async for chunk in response:
                if not chunk.choices:
                    continue
                token = chunk.choices[0].delta.content
                if token:
                    full_answer += token
                    yield f"data: {json.dumps({'token': token})}\n\n"
                    # yield control to the event loop
                    await asyncio.sleep(0)

            # Step 4: Persist conversation turn
            memory.append_turn("user", request.question)
            memory.append_turn("assistant", full_answer)
            memory.maybe_refresh_summary()

            # Step 5: Send final event with metadata
            final_event = {
                "done": True,
                "context_chunks": [c.model_dump() for c in chunks],
                "cache_hit": cache_hit,
                "tokens_used": tokens_used,
            }
            yield f"data: {json.dumps(final_event)}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        }
    )

@router.get("/registry", response_model=List[AgentDefinition])
async def list_agents():
    """Returns all available agents (base + user-configured)."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT agent_id, name, description, system_prompt, icon, is_system, base_agent_id "
            "FROM agent_definitions ORDER BY is_system DESC, name ASC"
        )
        rows = cursor.fetchall()

    return [
        AgentDefinition(
            agent_id=row["agent_id"],
            name=row["name"],
            description=row["description"],
            system_prompt=row["system_prompt"],
            icon=row["icon"],
            is_system=bool(row["is_system"]),
            base_agent_id=row["base_agent_id"],
        )
        for row in rows
    ]


# ── Agent Configuration (Clone + Customize) ───────────────────────────
@router.post("/configure", response_model=AgentDefinition)
async def configure_agent(request: AgentConfigRequest):
    """Clone a base agent with a custom system prompt and name."""
    # Verify the base agent exists
    base = _get_agent_definition(request.base_agent_id)
    if not base:
        raise HTTPException(status_code=404, detail=f"Base agent '{request.base_agent_id}' not found.")

    new_agent_id = f"custom_{uuid4().hex[:12]}"

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO agent_definitions (agent_id, name, description, system_prompt, base_agent_id, icon, is_system)
            VALUES (?, ?, ?, ?, ?, ?, 0)
        ''', (
            new_agent_id, request.name, request.description,
            request.system_prompt, request.base_agent_id, base["icon"]
        ))
        conn.commit()

    return AgentDefinition(
        agent_id=new_agent_id,
        name=request.name,
        description=request.description,
        system_prompt=request.system_prompt,
        icon=base["icon"],
        is_system=False,
        base_agent_id=request.base_agent_id,
    )


@router.delete("/configure/{agent_id}")
async def delete_configured_agent(agent_id: str):
    """Delete a user-configured agent. Cannot delete base system agents."""
    agent = _get_agent_definition(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found.")
    if agent["is_system"]:
        raise HTTPException(status_code=403, detail="Cannot delete system base agents.")

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM agent_definitions WHERE agent_id = ?", (agent_id,))
        conn.commit()

    return {"message": f"Agent '{agent_id}' deleted."}


# ── Helper ─────────────────────────────────────────────────────────────
def _get_agent_definition(agent_id: str) -> dict | None:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT agent_id, name, description, system_prompt, icon, is_system, base_agent_id "
            "FROM agent_definitions WHERE agent_id = ?",
            (agent_id,)
        )
        row = cursor.fetchone()
    if row:
        return dict(row)
    return None
