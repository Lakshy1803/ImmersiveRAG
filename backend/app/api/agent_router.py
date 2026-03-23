from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool
from typing import List
from uuid import uuid4
import json

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


# ── New Multi-Agent Chat Endpoint (Simplified Blocking) ────────────────
@router.post("/chat", response_model=AgentChatResponse)
async def agent_chat(request: AgentChatRequest):
    """
    Full RAG + LLM generation pipeline via LangGraph (Sync).
    Retrieves context from Qdrant, builds a prompt with conversation history,
    and generates an answer using the company LLM.
    """
    # 1. Look up the agent definition
    agent_def = _get_agent_definition(request.agent_id)
    if not agent_def:
        raise HTTPException(status_code=404, detail=f"Agent '{request.agent_id}' not found.")

    # 2. Run the LangGraph pipeline (Sync via Threadpool to avoid blocking loop)
    from app.engine.agents.graph_runner import run_agent_graph

    result = await run_in_threadpool(
        run_agent_graph,
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


# 🚫 Chat Stream endpoint removed as per simplification request.


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
