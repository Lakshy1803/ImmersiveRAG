---
description: Read all backend files and update context docs (context_b.md, context_f.md, architecture.md)
---
# Update Context Files After Code Changes

Run this workflow whenever backend or frontend code changes have been made and the context docs need to be refreshed.

## Steps

1. Read `my_plan.md` to understand the intended architecture and phase goals.

2. Explore the full backend directory to understand the current file layout:
   - `backend/app/api/` — routers and endpoints
   - `backend/app/core/` — config, scheduler, warnings
   - `backend/app/engine/agents/` — graph_runner, master_graph, state, llm_client, conversation_memory, subgraphs/
   - `backend/app/engine/ingestion/` — pipeline, parser, chunker, embedder
   - `backend/app/engine/retrieval/` — orchestrator
   - `backend/app/engine/tools/` — export_tools, template_extractor, and any new tools
   - `backend/app/engine/document_processing/` — OCR parser
   - `backend/app/models/` — api_models, domain_models
   - `backend/app/storage/` — vector_db, relations_db
   - `backend/app/main.py`

3. Read every file found above in full to understand the current implementation.

4. Explore the full frontend directory:
   - `frontend/src/app/` — layout, page, globals
   - `frontend/src/components/Chat/` — AgentChat, TemplateModal, and any new components
   - `frontend/src/components/Agents/` — AgentConfigModal
   - `frontend/src/components/Settings/` — LLMConfigModal
   - `frontend/src/components/Ingestion/` — IngestionManager, ConfigPanel, UploadZone
   - `frontend/src/lib/api.ts` — all API wrapper functions

5. Read the existing context docs to understand what is outdated:
   - `backend/context_b.md`
   - `frontend/context_f.md`
   - `architecture.md`

6. Compare existing docs against actual code and identify gaps/stale information:
   - New files added to `engine/tools/` (e.g., `template_extractor.py`)
   - New API endpoints added to `agent_router.py` or `admin_router.py`
   - New Pydantic models (`TemplateGenerateRequest`, etc.)
   - New frontend components (modals, tool panels)
   - New entries in `ImmersiveRagAPI` in `api.ts`
   - Updates to agent default `enabled_tools` in `relations_db.py`
   - Updates to `model_settings` keys (temperature, max_tokens, max_context_tokens, top_k)

7. Rewrite `backend/context_b.md` to accurately reflect:
   - Updated directory structure (all files in `engine/tools/`)
   - All API endpoints (both routers, all methods, request/response shapes)
   - Both LangGraph pipelines (RAG chat graph + Master Orchestrator)
   - All subgraphs with their node pipelines and outputs
   - AgentState TypedDict fields
   - Agent registry: default `enabled_tools` per base agent
   - SQLite tables and Qdrant collections
   - Ingestion lifecycle (stages and status transitions)
   - Memory strategy (3-tier)
   - All Pydantic API models including tool request/response shapes
   - All environment variables

8. Update `frontend/context_f.md` to reflect:
   - Updated component directory (new modals, new tool components)
   - New or changed endpoints that the frontend calls
   - Updated request/response shapes for tool endpoints
   - Note any new backend features not yet wired to frontend UI

9. Rewrite `architecture.md` to reflect the full system design:
   - System overview diagram (text)
   - Both LangGraph engines with flow diagrams
   - Ingestion pipeline lifecycle (numbered steps)
   - Storage architecture (SQLite tables + Qdrant collections)
   - Agent registry design (base agents and their default tools)
   - Memory strategy table
   - Tool services table (all tools, endpoints, and implementation details)
   - Config/env variables
   - Phase 1 completion status vs. `my_plan.md`

> **Note:** Only update context docs — do not change any source code. The frontend code is NOT being changed in this workflow step; `context_f.md` only reflects what the backend exposes and what components exist.
