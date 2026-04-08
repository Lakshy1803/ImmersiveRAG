from fastapi import APIRouter, HTTPException, Request, UploadFile, File
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import StreamingResponse
from typing import List, Optional
from uuid import uuid4
import json
from pydantic import BaseModel
from fastapi.responses import Response

class ExportRequest(BaseModel):
    content: str

class TemplateGenerateRequest(BaseModel):
    template_markdown: str
    filled_content: str
    style_config: Optional[dict] = None

from app.models.api_models import (
    AgentQueryRequest, AgentContextResponse, ContextChunk,
    AgentChatRequest, AgentChatResponse,
    AgentDefinition, AgentConfigRequest, MasterAgentConfigRequest,
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
        model_settings=agent_def.get("model_settings", {})
    )

    # 3. Map raw chunk dicts back to ContextChunk models
    context_chunks = [ContextChunk(**c) for c in result.get("context_chunks", [])]

    return AgentChatResponse(
        answer=result["answer"],
        context_chunks=context_chunks,
        tokens_used=result["tokens_used"],
        cache_hit=result["cache_hit"],
    )


# ── Streaming Chat Endpoint (SSE) ─────────────────────────────────────
@router.post("/chat/stream")
async def agent_chat_stream(request: AgentChatRequest):
    """
    Full RAG + LLM streaming pipeline.
    Returns a Server-Sent Events (SSE) stream.

    Event types:
      data: {"type": "context", "chunks": [...], "cache_hit": bool, "tokens_used": int}
      data: {"type": "chunk",   "text": "..."}   ← one per LLM token
      data: {"type": "done"}
    """
    agent_def = _get_agent_definition(request.agent_id)
    if not agent_def:
        raise HTTPException(status_code=404, detail=f"Agent '{request.agent_id}' not found.")

    # Master Agent → intent-routing orchestrator graph
    if agent_def.get("kind") == "master":
        from app.engine.agents.master_router_graph import stream_master_router_graph

        # Resolve sub-agents
        sub_agent_ids = agent_def.get("enabled_tools", [])  # repurposed field
        sub_agents = [_get_agent_definition(aid) for aid in sub_agent_ids]
        sub_agents = [a for a in sub_agents if a]  # filter None

        def generate_master():
            yield from stream_master_router_graph(
                question=request.question,
                agent_id=request.agent_id,
                session_id=request.session_id,
                sub_agents=sub_agents,
                model_settings=agent_def.get("model_settings", {}),
            )

        return StreamingResponse(
            generate_master(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    # Standard Agent → regular RAG graph
    from app.engine.agents.graph_runner import stream_agent_graph

    def generate():
        yield from stream_agent_graph(
            question=request.question,
            agent_id=request.agent_id,
            session_id=request.session_id,
            system_prompt=agent_def["system_prompt"],
            model_settings=agent_def.get("model_settings", {}),
        )

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/registry", response_model=List[AgentDefinition])
async def list_agents():
    """Returns all available agents (base + user-configured)."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT agent_id, name, description, system_prompt, icon, is_system, base_agent_id, "
            "enabled_tools, config_json, kind, is_published "
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
            enabled_tools=json.loads(row["enabled_tools"]) if row["enabled_tools"] else [],
            model_settings=json.loads(row["config_json"]) if row["config_json"] else {},
            kind=row["kind"] or "standard",
            is_published=bool(row["is_published"]),
        )
        for row in rows
    ]


# ── Tool Usage Endpoints ───────────────────────────────────────────────
@router.post("/tools/export/csv")
async def export_csv(request: ExportRequest):
    """Exports tabular data from a message into CSV."""
    from app.engine.tools.export_tools import extract_tables_to_csv
    csv_data = extract_tables_to_csv(request.content)
    return Response(
        content=csv_data, 
        media_type="text/csv", 
        headers={"Content-Disposition": "attachment; filename=export.csv"}
    )

@router.post("/tools/export/pdf")
async def export_pdf(request: ExportRequest):
    """Generates a PDF report from the markdown answer."""
    from app.engine.tools.export_tools import generate_pdf_from_markdown
    try:
        pdf_data = generate_pdf_from_markdown(request.content)
        return Response(
            content=pdf_data, 
            media_type="application/pdf", 
            headers={"Content-Disposition": "attachment; filename=report.pdf"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF Generation failed: {str(e)}")

@router.post("/tools/generate/template")
async def generate_template(request: TemplateGenerateRequest):
    """Generates a branded PDF from a template skeleton filled with context content."""
    from app.engine.tools.export_tools import generate_template_pdf
    try:
        pdf_data = generate_template_pdf(
            request.template_markdown,
            request.filled_content,
            style_config=request.style_config
        )
        return Response(
            content=pdf_data,
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=template_document.pdf"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Template generation failed: {str(e)}")


@router.post("/tools/templates/extract")
async def extract_template_style(file: UploadFile = File(...)):
    """Upload a sample PDF to extract its brand color schema and font family."""
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")
    try:
        from app.engine.tools.template_extractor import extract_style_from_pdf
        pdf_bytes = await file.read()
        style = await run_in_threadpool(extract_style_from_pdf, pdf_bytes)
        return style
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Style extraction failed: {str(e)}")


# ── Master Agent Configuration ─────────────────────────────────────────
@router.post("/configure/master", response_model=AgentDefinition)
async def configure_master_agent(request: MasterAgentConfigRequest):
    """Create or update a Master Orchestrator agent with a list of sub-agent IDs."""
    with get_connection() as conn:
        cursor = conn.cursor()
        if request.agent_id:
            existing = _get_agent_definition(request.agent_id)
            if not existing:
                raise HTTPException(status_code=404, detail=f"Agent '{request.agent_id}' not found.")
            if existing.get("is_system"):
                raise HTTPException(status_code=403, detail="Cannot edit system agents.")
            cursor.execute('''
                UPDATE agent_definitions
                SET name=?, description=?, enabled_tools=?, is_published=?
                WHERE agent_id=?
            ''', (
                request.name, request.description,
                json.dumps(request.sub_agent_ids),
                int(request.is_published),
                request.agent_id
            ))
            agent_id_to_return = request.agent_id
        else:
            agent_id_to_return = f"master_{uuid4().hex[:12]}"
            cursor.execute('''
                INSERT INTO agent_definitions
                  (agent_id, name, description, system_prompt, base_agent_id, icon, is_system, enabled_tools, config_json, kind, is_published)
                VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?, 'master', ?)
            ''', (
                agent_id_to_return, request.name, request.description,
                "You are a Master Orchestrator that intelligently delegates user requests across your configured agent army.",
                "master_orchestrator", "hub",
                json.dumps(request.sub_agent_ids), "{}",
                int(request.is_published)
            ))
        conn.commit()

    row = _get_agent_definition(agent_id_to_return)
    # Populate sub_agents details
    sub_agents_detail = [
        {"agent_id": a["agent_id"], "name": a["name"], "icon": a["icon"]}
        for sid in request.sub_agent_ids
        if (a := _get_agent_definition(sid))
    ]
    return AgentDefinition(
        agent_id=agent_id_to_return,
        name=request.name,
        description=request.description,
        system_prompt=row["system_prompt"],
        icon="hub",
        is_system=False,
        base_agent_id="master_orchestrator",
        enabled_tools=request.sub_agent_ids,
        model_settings={},
        kind="master",
        is_published=request.is_published,
        sub_agents=sub_agents_detail,
    )


@router.post("/configure/master/{agent_id}/publish", response_model=AgentDefinition)
async def publish_master_agent(agent_id: str):
    """Toggle a Master Agent to published state so the team can discover and use it."""
    agent = _get_agent_definition(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found.")
    if agent.get("kind") != "master":
        raise HTTPException(status_code=400, detail="Only Master Agents can be published.")

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE agent_definitions SET is_published=1 WHERE agent_id=?", (agent_id,))
        conn.commit()

    row = _get_agent_definition(agent_id)
    sub_agent_ids = row.get("enabled_tools", [])
    sub_agents_detail = [
        {"agent_id": a["agent_id"], "name": a["name"], "icon": a["icon"]}
        for sid in sub_agent_ids
        if (a := _get_agent_definition(sid))
    ]
    return AgentDefinition(
        agent_id=agent_id,
        name=row["name"],
        description=row["description"],
        system_prompt=row["system_prompt"],
        icon="hub",
        is_system=False,
        base_agent_id="master_orchestrator",
        enabled_tools=sub_agent_ids,
        model_settings=row.get("model_settings", {}),
        kind="master",
        is_published=True,
        sub_agents=sub_agents_detail,
    )


@router.get("/published", response_model=List[AgentDefinition])
async def list_published_workflows():
    """Returns all published Master Agents (team-discoverable workflows)."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT agent_id, name, description, system_prompt, icon, is_system, "
            "base_agent_id, enabled_tools, config_json, kind, is_published "
            "FROM agent_definitions WHERE kind='master' AND is_published=1 ORDER BY name ASC"
        )
        rows = cursor.fetchall()

    result = []
    for row in rows:
        sub_agent_ids = json.loads(row["enabled_tools"]) if row["enabled_tools"] else []
        sub_agents_detail = [
            {"agent_id": a["agent_id"], "name": a["name"], "icon": a["icon"]}
            for sid in sub_agent_ids
            if (a := _get_agent_definition(sid))
        ]
        result.append(AgentDefinition(
            agent_id=row["agent_id"],
            name=row["name"],
            description=row["description"],
            system_prompt=row["system_prompt"],
            icon="hub",
            is_system=bool(row["is_system"]),
            base_agent_id=row["base_agent_id"],
            enabled_tools=sub_agent_ids,
            model_settings=json.loads(row["config_json"]) if row["config_json"] else {},
            kind="master",
            is_published=True,
            sub_agents=sub_agents_detail,
        ))
    return result


# ── Agent Configuration (Clone + Customize or Update) ─────────────────
@router.post("/configure", response_model=AgentDefinition)
async def configure_agent(request: AgentConfigRequest):
    """Clone a base agent or update an existing custom agent with new settings."""
    # Verify the base agent exists (if creating or editing an agent based on one)
    base = _get_agent_definition(request.base_agent_id)
    if not base:
        raise HTTPException(status_code=404, detail=f"Base agent '{request.base_agent_id}' not found.")

    with get_connection() as conn:
        cursor = conn.cursor()
        
        if request.agent_id:
            # UPDATE existing custom agent
            existing = _get_agent_definition(request.agent_id)
            if not existing:
                raise HTTPException(status_code=404, detail=f"Agent '{request.agent_id}' not found.")
            if existing["is_system"]:
                raise HTTPException(status_code=403, detail="Cannot edit system base agents.")
            
            cursor.execute('''
                UPDATE agent_definitions 
                SET name = ?, description = ?, system_prompt = ?, base_agent_id = ?, enabled_tools = ?, config_json = ?
                WHERE agent_id = ?
            ''', (
                request.name, request.description, request.system_prompt, 
                request.base_agent_id, json.dumps(request.enabled_tools), 
                json.dumps(request.model_settings), request.agent_id
            ))
            agent_id_to_return = request.agent_id
        else:
            # CREATE new agent
            agent_id_to_return = f"custom_{uuid4().hex[:12]}"
            cursor.execute('''
                INSERT INTO agent_definitions (agent_id, name, description, system_prompt, base_agent_id, icon, is_system, enabled_tools, config_json)
                VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?)
            ''', (
                agent_id_to_return, request.name, request.description,
                request.system_prompt, request.base_agent_id, base["icon"],
                json.dumps(request.enabled_tools), json.dumps(request.model_settings)
            ))
        
        conn.commit()

    return AgentDefinition(
        agent_id=agent_id_to_return,
        name=request.name,
        description=request.description,
        system_prompt=request.system_prompt,
        icon=base["icon"],
        is_system=False,
        base_agent_id=request.base_agent_id,
        enabled_tools=request.enabled_tools,
        model_settings=request.model_settings,
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
            "SELECT agent_id, name, description, system_prompt, icon, is_system, base_agent_id, "
            "enabled_tools, config_json, kind, is_published "
            "FROM agent_definitions WHERE agent_id = ?",
            (agent_id,)
        )
        row = cursor.fetchone()
    if row:
        row_dict = dict(row)
        if isinstance(row_dict.get("enabled_tools"), str):
            row_dict["enabled_tools"] = json.loads(row_dict["enabled_tools"])
        if isinstance(row_dict.get("config_json"), str):
            row_dict["model_settings"] = json.loads(row_dict["config_json"])
        else:
            row_dict["model_settings"] = {}
        row_dict["kind"] = row_dict.get("kind") or "standard"
        row_dict["is_published"] = bool(row_dict.get("is_published", 0))
        return row_dict
    return None


class TestWorkflowRequest(BaseModel):
    user_query: str = "What are the key terms in the document?"
    workflow_agents: list[str] = ["document_agent", "retrieval_agent", "analysis_agent", "report_agent"]
    agent_id: str = "default_setup"
    session_id: str = "test_session_1"
    uploaded_docs: list[dict] = [
        {"filename": "sample.png", "path": "test.png", "type": "png"}
    ]

@router.post("/test_master_workflow")
async def test_master_workflow(request: TestWorkflowRequest):
    """
    Test endpoint for running the dynamic Master Orchestrator graph.
    Pass in a custom 'workflow_agents' list to see routing in action.
    """
    from app.engine.agents.master_graph import master_orchestrator
    
    # Seed the unified AgentState
    initial_state = {
        "user_query": request.user_query,
        "agent_id": request.agent_id,
        "session_id": request.session_id,
        "workflow_agents": request.workflow_agents,
        "current_step_index": 0,
        "uploaded_docs": request.uploaded_docs,
        "document_chunks": [],
        "retrieved_docs": [],
        "analysis_result": "",
        "final_report": "",
        "tool_outputs": {},
        "status": "running"
    }
    
    # Execute orchestrator using full async native call
    result = await master_orchestrator.ainvoke(initial_state)
    
    return result
